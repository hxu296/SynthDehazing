# -*- coding: utf-8 -*-
"""
Created on Tue Jul 14 20:11:02 2020

@author: delgallegon
"""
import os
import torch
from PIL import Image
import cv2
import numpy as np
import matplotlib.pyplot as plt
from torch.utils import data
import torch.nn as nn
from utils import tensor_utils
from torchvision.utils import save_image
import torchvision.transforms as transforms
import constants

DATASET_DIV2K_PATH = "E:/DIV2K_train_HR/"
SAVE_PATH = "E:/VEMON_Transfer/train/C/"

class AddGaussianNoise(object):
    def __init__(self, mean=0.0, std=1.0):
        self.std = std
        self.mean = mean
        
    def __call__(self, tensor):
        return tensor + torch.randn(tensor.size()) * self.std + self.mean
    
    def __repr__(self):
        return self.__class__.__name__ + '(mean={0}, std={1})'.format(self.mean, self.std)
    
def assemble_img_list(path, num_image_to_load = -1):
    img_list = []
    
    for (root, dirs, files) in os.walk(path):
        for f in files:
            file_name = os.path.join(root, f)
            img_list.append(file_name)
    
    return img_list


def unsharp_mask(div2k_img):
    gaussian_3 = cv2.GaussianBlur(div2k_img, (9,9), 10.0)
    unsharp_image = cv2.addWeighted(div2k_img, 1.5, gaussian_3, -0.5, 0)
    
    return unsharp_image

def create_img_data(dataset_path, save_path, filename_format, img_size, patch_size, repeats):
    img_list = assemble_img_list(dataset_path)
    count = 0
    for k in range(len(img_list)):
        normal_img = cv2.imread(img_list[k])
        normal_img = cv2.cvtColor(normal_img, cv2.COLOR_BGR2RGB)
        
        final_op = transforms.Compose([transforms.ToPILImage(), 
                                       transforms.RandomHorizontalFlip(),
                                       transforms.Resize(img_size),
                                       transforms.RandomCrop(patch_size),
                                       transforms.ToTensor()])
        
        for i in range(repeats):
            file_name = save_path + filename_format % count
            
            new_img = final_op(normal_img).numpy()
            final_img = unsharp_mask(new_img)
            
            new_img = np.moveaxis(new_img, -1, 0)
            new_img = np.moveaxis(new_img, -1, 0)
            final_img = np.moveaxis(final_img, -1, 0)
            final_img = np.moveaxis(final_img, -1, 0)
            
            # plt.imshow(new_img)
            # plt.show()
            # plt.imshow(final_img)
            # plt.show()

            cv2.imwrite(file_name, cv2.cvtColor(cv2.convertScaleAbs(final_img, alpha=255.0), cv2.COLOR_BGR2RGB))
            print("Saved: ", file_name)
            count = count + 1


def create_paired_img_data(dataset_path_a, dataset_path_b, save_path_a, save_path_b, filename_format, img_size, patch_size, repeats):
    img_list_a = assemble_img_list(dataset_path_a)
    img_list_b = assemble_img_list(dataset_path_b)

    count = 0
    for k in range(len(img_list_a)):
        img_a = cv2.imread(img_list_a[k])
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)
        img_b = cv2.imread(img_list_b[k])
        img_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB)

        initial_transform_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(img_size),
        ])

        for i in range(repeats):
            file_name_a = save_path_a + filename_format % count
            file_name_b = save_path_b + filename_format % count

            img_a_patch = initial_transform_op(img_a)
            img_b_patch = initial_transform_op(img_b)

            crop_indices = transforms.RandomCrop.get_params(img_a_patch, output_size=patch_size)
            i, j, h, w = crop_indices

            img_a_patch = transforms.functional.crop(img_a_patch, i, j, h, w)
            img_b_patch = transforms.functional.crop(img_b_patch, i, j, h, w)

            img_a_patch.save(file_name_a)
            img_b_patch.save(file_name_b)
            print("Saved: ", file_name_a, file_name_b)
            count = count + 1
  
def create_gta_noisy_data():
    NOISY_SAVE_PATH = "E:/Noisy GTA/noisy/"
    CLEAN_SAVE_PATH = "E:/Noisy GTA/clean/"
    gta_clean_data = assemble_img_list(constants.DATASET_GTA_PATH_2)
    count = 0
    for k in range(len(gta_clean_data)):
        normal_img = cv2.imread(gta_clean_data[k])
        normal_img = cv2.cvtColor(normal_img, cv2.COLOR_BGR2RGB)
        transform_op = transforms.Compose([transforms.ToPILImage(),
                                           transforms.ColorJitter(brightness=(1.25, 1.8)),
                                           transforms.ToTensor(),
                                           AddGaussianNoise(std=0.15)]
                                          )
        
        final_img = transform_op(normal_img)
        file_name = NOISY_SAVE_PATH + "gta_noisy_%d.png" % count
        save_image(final_img, file_name)
        print("Saved: ", file_name)
        
        file_name = CLEAN_SAVE_PATH + "gta_clean_%d.png" % count
        save_image(transforms.ToTensor()(normal_img), file_name)
        
        count = count + 1

def create_hazy_data(offset):
    clean_video_path = "D:/Users/delgallegon/Documents/GithubProjects/NeuralNets-SynthWorkplace/Recordings/synth_5_clean.mp4"
    hazy_video_path = "D:/Users/delgallegon/Documents/GithubProjects/NeuralNets-SynthWorkplace/Recordings/synth_5_haze.mp4"
    
    CLEAN_SAVE_PATH = "E:/Synth Hazy - B/clean/"
    HAZY_SAVE_PATH = "E:/Synth Hazy - B/hazy/"
    
    vidcap = cv2.VideoCapture(clean_video_path)
    count = offset
    success,image = vidcap.read()
    
    success = True
    while success:
        success,image = vidcap.read()
        if(success):
            w,h,c = np.shape(image)
            image = cv2.resize(image, (int(h/2), int(w/2)), interpolation = cv2.INTER_CUBIC)
            cv2.imwrite(CLEAN_SAVE_PATH + "synth_%d.png" % count, image)
            print("Saved clean: synth_%d.png" % count)
            count += 1
    
    #for noisy
    vidcap = cv2.VideoCapture(hazy_video_path)
    count = offset
    success,image = vidcap.read()
    
    success = True
    while success:
        success,image = vidcap.read()
        if(success):
            w,h,c = np.shape(image)
            image = cv2.resize(image, (int(h/4), int(w/4)), interpolation = cv2.INTER_CUBIC)
            cv2.imwrite(HAZY_SAVE_PATH + "synth_%d.png" % count, image)
            print("Saved hazy: synth_%d.png" % count)
            count += 1
    
def main():
    #create_gta_noisy_data()
    #create_div2k_data()
    #create_hazy_data(0)

    PATH_A = "E:/Synth Hazy/hazy/"
    SAVE_PATH_A = "E:/Synth Hazy - Patch/hazy/"

    PATH_B = "E:/Synth Hazy/clean/"
    SAVE_PATH_B = "E:/Synth Hazy - Patch/clean/"
    create_paired_img_data(PATH_A, PATH_B, SAVE_PATH_A, SAVE_PATH_B, "frame_%d.png", constants.TEST_IMAGE_SIZE, constants.PATCH_IMAGE_SIZE, 10)

if __name__=="__main__": 
    main()   