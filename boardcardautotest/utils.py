import os
import os.path as osp

import cv2 as cv
import numpy as np
import pytesseract


def obt_roi(image):
    if len(image.shape) > 2:
        image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    _, bin_image = cv.threshold(image, 0, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)
    contours, hierarchy = cv.findContours(bin_image, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    return contours
    
    for cnt in contours:
        x, y, w, h = cv.boundingRect(cnt)
        cv.rectangle(image, (x, y), (x+w, y+h), (255, 0, 255), -1)
        cv.namedWindow("images", cv.WINDOW_NORMAL)
        cv.imshow("images", image)
        if cv.waitKey(0) == ord("q"):
            cv.destroyAllWindows()


def ocr_processor(image):
    if len(image.shape) > 2:
        image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    _, bin_image = cv.threshold(image, 0, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)
    return pytesseract.image_to_string(bin_image, lang='eng')


if __name__ == "__main__":
    image_path = "boardcardautotest/test.jpeg"
    image = cv.imread(image_path)
    # contours = obt_roi(image)
    # for cnt in contours:
    #     x, y, w, h = cv.boundingRect(cnt)
    #     area = cv.contourArea(cnt)
    #     if area>120000:
    #         # cv.drawContours(image, cnt, -1, (0, 0, 255), 3)
    #         roi_image = image[y:y+h, x:x+w]
    #         image_txt = ocr_processor(roi_image)
    #         print(image_txt)
            
    #         cv.namedWindow("roi_image", cv.WINDOW_NORMAL)
    #         cv.imshow("roi_image", roi_image)
    #         if cv.waitKey(0) == ord("q"):
    #             cv.destroyAllWindows()

    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    _, bin_image = cv.threshold(gray, 0, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)
    
    image_txt = ocr_processor(bin_image)
    print(image_txt)
    
    cv.namedWindow("images", cv.WINDOW_NORMAL)
    cv.imshow("images", bin_image)
    cv.waitKey(0)
    cv.destroyAllWindows()
