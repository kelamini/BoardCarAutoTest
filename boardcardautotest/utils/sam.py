import os
import logging
import cv2
import numpy as np
from typing import List, Dict, Optional

import onnxruntime
from segment_anything import sam_model_registry, SamPredictor

logger = logging.getLogger(__name__)

VITH_CHECKPOINT = os.environ.get("VITH_CHECKPOINT", "sam_vit_h_4b8939.pth")
ONNX_CHECKPOINT = os.environ.get("ONNX_CHECKPOINT", "sam_onnx_quantized_example.onnx")


class SAMPredictor:
    def __init__(self, model_choice):
        if model_choice == 'ONNX':
            self.model_checkpoint = VITH_CHECKPOINT
            if self.model_checkpoint is None:
                raise FileNotFoundError("VITH_CHECKPOINT is not set: please set it to the path to the SAM checkpoint")
            if ONNX_CHECKPOINT is None:
                raise FileNotFoundError("ONNX_CHECKPOINT is not set: please set it to the path to the ONNX checkpoint")
            logger.info(f"Using ONNX checkpoint {ONNX_CHECKPOINT} and SAM checkpoint {self.model_checkpoint}")

            self.ort = onnxruntime.InferenceSession(ONNX_CHECKPOINT)
            reg_key = "vit_h"
        
        self.model_choice = model_choice
        self.device = "cpu"

        sam = sam_model_registry[reg_key](checkpoint=self.model_checkpoint)
        sam.to(device=self.device)
        self.predictor = SamPredictor(sam)

        sam = sam_model_registry[reg_key](checkpoint=self.model_checkpoint)
        sam.to(device=self.device)
        self.predictor = SamPredictor(sam)

    def set_image(self, img_path, calculate_embeddings=True):
        payload = self.cache.get(img_path)
        if payload is None:
            # Get image and embeddings
            logger.debug(f'Payload not found for {img_path} in `IN_MEM_CACHE`: calculating from scratch')
            # image_path = get_image_local_path(
            #     img_path,
            #     label_studio_access_token=LABEL_STUDIO_ACCESS_TOKEN,
            #     label_studio_host=LABEL_STUDIO_HOST
            # )
            image = cv2.imread(img_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            self.predictor.set_image(image)
            payload = {'image_shape': image.shape[:2]}
            logger.debug(f'Finished set_image({img_path}) in `IN_MEM_CACHE`: image shape {image.shape[:2]}')
            if calculate_embeddings:
                image_embedding = self.predictor.get_image_embedding().cpu().numpy()
                payload['image_embedding'] = image_embedding
                logger.debug(f'Finished storing embeddings for {img_path} in `IN_MEM_CACHE`: '
                             f'embedding shape {image_embedding.shape}')
            self.cache.put(img_path, payload)
        else:
            logger.debug(f"Using embeddings for {img_path} from `IN_MEM_CACHE`")
        return payload

    def predict_onnx(
        self,
        img_path,
        point_coords: Optional[List[List]] = None,
        point_labels: Optional[List] = None,
        input_box: Optional[List] = None
    ):
        # calculate embeddings
        payload = self.set_image(img_path, calculate_embeddings=True)
        image_shape = payload['image_shape']
        image_embedding = payload['image_embedding']

        onnx_point_coords = np.array(point_coords, dtype=np.float32) if point_coords else None
        onnx_point_labels = np.array(point_labels, dtype=np.float32) if point_labels else None
        onnx_box_coords = np.array(input_box, dtype=np.float32).reshape(2, 2) if input_box else None

        onnx_coords, onnx_labels = None, None
        if onnx_point_coords is not None and onnx_box_coords is not None:
            # both keypoints and boxes are present
            onnx_coords = np.concatenate([onnx_point_coords, onnx_box_coords], axis=0)[None, :, :]
            onnx_labels = np.concatenate([onnx_point_labels, np.array([2, 3])], axis=0)[None, :].astype(np.float32)

        elif onnx_point_coords is not None:
            # only keypoints are present
            onnx_coords = np.concatenate([onnx_point_coords, np.array([[0.0, 0.0]])], axis=0)[None, :, :]
            onnx_labels = np.concatenate([onnx_point_labels, np.array([-1])], axis=0)[None, :].astype(np.float32)

        elif onnx_box_coords is not None:
            # only boxes are present
            raise NotImplementedError("Boxes without keypoints are not supported yet")

        onnx_coords = self.predictor.transform.apply_coords(onnx_coords, image_shape).astype(np.float32)

        # TODO: support mask inputs
        onnx_mask_input = np.zeros((1, 1, 256, 256), dtype=np.float32)

        onnx_has_mask_input = np.zeros(1, dtype=np.float32)

        ort_inputs = {
            "image_embeddings": image_embedding,
            "point_coords": onnx_coords,
            "point_labels": onnx_labels,
            "mask_input": onnx_mask_input,
            "has_mask_input": onnx_has_mask_input,
            "orig_im_size": np.array(image_shape, dtype=np.float32)
        }

        masks, prob, low_res_logits = self.ort.run(None, ort_inputs)
        masks = masks > self.predictor.model.mask_threshold
        mask = masks[0, 0, :, :].astype(np.uint8)  # each mask has shape [H, W]
        prob = float(prob[0][0])
        # TODO: support the real multimask output as in https://github.com/facebookresearch/segment-anything/blob/main/notebooks/predictor_example.ipynb
        return {
            'masks': [mask],
            'probs': [prob]
        }

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """ Returns the predicted mask for a smart keypoint that has been placed."""

        from_name, to_name, value = self.get_first_tag_occurence('BrushLabels', 'Image')

        if not context or not context.get('result'):
            # if there is no context, no interaction has happened yet
            return []

        image_width = context['result'][0]['original_width']
        image_height = context['result'][0]['original_height']

        # collect context information
        point_coords = []
        point_labels = []
        input_box = None
        selected_label = None
        for ctx in context['result']:
            x = ctx['value']['x'] * image_width / 100
            y = ctx['value']['y'] * image_height / 100
            ctx_type = ctx['type']
            selected_label = ctx['value'][ctx_type][0]
            if ctx_type == 'keypointlabels':
                point_labels.append(int(ctx['is_positive']))
                point_coords.append([int(x), int(y)])
            elif ctx_type == 'rectanglelabels':
                box_width = ctx['value']['width'] * image_width / 100
                box_height = ctx['value']['height'] * image_height / 100
                input_box = [int(x), int(y), int(box_width + x), int(box_height + y)]

        print(f'Point coords are {point_coords}, point labels are {point_labels}, input box is {input_box}')

        img_path = tasks[0]['data'][value]
        predictor_results = self.predict_onnx(
            img_path=img_path,
            point_coords=point_coords or None,
            point_labels=point_labels or None,
            input_box=input_box
        )

        predictions = self.get_results(
            masks=predictor_results['masks'],
            probs=predictor_results['probs'],
            width=image_width,
            height=image_height,
            from_name=from_name,
            to_name=to_name,
            label=selected_label)

        return predictions


if __name__ == "__main__":
    pass
