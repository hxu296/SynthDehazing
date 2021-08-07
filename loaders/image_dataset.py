# -*- coding: utf-8 -*-
"""
Created on Fri Jun  7 18:14:21 2019

Pytorch image dataset
@author: delgallegon
"""
import math

import torch
import cv2
import numpy as np
from torch.utils import data
from matplotlib import pyplot as plt
from ast import literal_eval
import torchvision.transforms as transforms
import constants
from utils import dehazing_proper
import kornia

class DehazingDataset(data.Dataset):
    def __init__(self, image_list_a, depth_dir, crop_size, should_crop, return_ground_truth):
        self.image_list_a = image_list_a
        self.depth_dir = depth_dir
        self.crop_size = crop_size
        self.should_crop = should_crop
        self.return_ground_truth = return_ground_truth
        self.resize_shape = (256, 256)

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(self.resize_shape)
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

        self.depth_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        clear_img = cv2.imread(img_id);
        clear_img = cv2.cvtColor(clear_img, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        clear_img = cv2.resize(clear_img, self.resize_shape)
        clear_img_uint = clear_img
        clear_img = cv2.normalize(clear_img, dst=None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        img_id = self.depth_dir + file_name
        transmission_img = cv2.imread(img_id)
        transmission_img = cv2.cvtColor(transmission_img, cv2.COLOR_BGR2GRAY)
        transmission_img = cv2.resize(transmission_img, np.shape(clear_img[:, :, 0]))
        transmission_img = cv2.normalize(transmission_img, dst=None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        T = dehazing_proper.generate_transmission(1 - transmission_img, np.random.uniform(0.7, 0.95)) #also include clear samples
        #T = dehazing_proper.generate_transmission(1 - transmission_img, np.random.normal(1.25, 0.75))
        #T = dehazing_proper.generate_transmission(1 - transmission_img, np.random.normal(0.625, 0.55))

        #formulate hazy img
        atmosphere = [0.0, 0.0, 0.0]
        spread = 0.125
        atmosphere[0] = np.random.uniform(AirlightDataset.ATMOSPHERE_MIN, AirlightDataset.ATMOSPHERE_MAX)
        atmosphere[1] = np.random.normal(atmosphere[0], spread)  # randomize by gaussian on other channels using R channel atmosphere
        atmosphere[2] = np.random.normal(atmosphere[0], spread)

        img_atmosphere = np.zeros_like(clear_img)
        img_atmosphere[:, :, 0] = atmosphere[0] * (1 - T)
        img_atmosphere[:, :, 1] = atmosphere[1] * (1 - T)
        img_atmosphere[:, :, 2] = atmosphere[2] * (1 - T)

        hazy_img_like = np.zeros_like(clear_img)
        T = np.resize(T, np.shape(clear_img[:, :, 0]))
        hazy_img_like[:, :, 0] = (clear_img[:, :, 0] * T) + img_atmosphere[:, :, 0]
        hazy_img_like[:, :, 1] = (clear_img[:, :, 1] * T) + img_atmosphere[:, :, 1]
        hazy_img_like[:, :, 2] = (clear_img[:, :, 2] * T) + img_atmosphere[:, :, 2]

        img_a = cv2.normalize(hazy_img_like, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)

        #loosen T, A prediction
        #T = np.maximum(T, 0.5)
        #img_atmosphere = np.maximum(img_atmosphere, 0.5)
        #T = T * 0.6
        #img_atmosphere = img_atmosphere * 0.6

        transmission_img = cv2.resize(T, self.resize_shape)

        if(self.should_crop):
            crop_indices = transforms.RandomCrop.get_params(img_a, output_size=self.crop_size)
            i, j, h, w = crop_indices

            img_a = transforms.functional.crop(img_a, i, j, h, w)
            #img_b = transforms.functional.crop(img_b, i, j, h, w)
            #img_a = img_a[i: i + h, j: j + w]
            hazy_img_like = hazy_img_like[i: i + h, j: j + w]
            transmission_img = transmission_img[i: i + h, j: j + w]
            img_atmosphere = img_atmosphere[i: i + h, j: j + w]
            clear_img_uint = clear_img_uint[i: i + h, j: j + w]


        img_a = self.final_transform_op(hazy_img_like)
        transmission_img = self.depth_transform_op(transmission_img)
        img_atmosphere = self.final_transform_op(img_atmosphere)

        if(self.return_ground_truth):
            ground_truth_img = self.final_transform_op(clear_img_uint)
            return file_name, img_a, transmission_img, ground_truth_img, img_atmosphere
        else:
            return file_name, img_a, transmission_img, img_atmosphere #hazy albedo img, transmission map

    def __len__(self):
        return len(self.image_list_a)


class DehazingDatasetTest(data.Dataset):
    def __init__(self, image_list_a):
        self.image_list_a = image_list_a

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 256))
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        img_a = cv2.imread(img_id);
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        img_a = cv2.normalize(img_a, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)
        img_a = self.final_transform_op(img_a)

        return file_name, img_a

    def __len__(self):
        return len(self.image_list_a)

class DehazingDatasetPaired(data.Dataset):
    def __init__(self, image_list_a, image_list_b, resize_shape):
        self.image_list_a = image_list_a
        self.image_list_b = image_list_b
        self.resize_shape = resize_shape

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(self.resize_shape)
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        img_a = cv2.imread(img_id);
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        img_a = cv2.normalize(img_a, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)
        img_a = self.final_transform_op(img_a)

        img_id = self.image_list_b[idx]
        img_b = cv2.imread(img_id);
        img_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        img_b = cv2.normalize(img_b, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_b = self.initial_img_op(img_b)
        img_b = self.final_transform_op(img_b)

        return file_name, img_a, img_b

    def __len__(self):
        return len(self.image_list_a)

class TransmissionAlbedoDataset(data.Dataset):
    def __init__(self, image_list_a, depth_dir, crop_size, should_crop, return_ground_truth):
        self.image_list_a = image_list_a
        self.depth_dir = depth_dir
        self.crop_size = crop_size
        self.should_crop = should_crop
        self.return_ground_truth = return_ground_truth
        self.resize_shape = (256, 256)

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(self.resize_shape)
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

        self.depth_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        clear_img = cv2.imread(img_id);
        clear_img = cv2.cvtColor(clear_img, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        clear_img = cv2.resize(clear_img, self.resize_shape)
        clear_img_uint = clear_img
        clear_img = cv2.normalize(clear_img, dst=None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        img_id = self.depth_dir + file_name
        transmission_img = cv2.imread(img_id)
        transmission_img = cv2.cvtColor(transmission_img, cv2.COLOR_BGR2GRAY)
        transmission_img = cv2.resize(transmission_img, np.shape(clear_img[:, :, 0]))
        transmission_img = cv2.normalize(transmission_img, dst=None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        #T = dehazing_proper.generate_transmission(1 - img_b, np.random.uniform(0.0, 2.5)) #also include clear samples
        #T = dehazing_proper.generate_transmission(1 - img_b, np.random.normal(1.25, 0.75))
        T = dehazing_proper.generate_transmission(1 - transmission_img, np.random.normal(1.8, 0.75))
        #T = np.maximum(T, 0.7)

        #formulate hazy img
        atmosphere = [0.0, 0.0, 0.0]
        #spread = 0.025
        spread = 0.025
        atmosphere[0] = np.random.normal(AirlightDataset.atmosphere_mean(), AirlightDataset.atmosphere_std())
        atmosphere[1] = np.random.normal(atmosphere[0], spread)  # randomize by gaussian on other channels using R channel atmosphere
        atmosphere[2] = np.random.normal(atmosphere[0], spread)

        img_atmosphere = np.zeros_like(clear_img)
        img_atmosphere[:, :, 0] = atmosphere[0] * (1 - T)
        img_atmosphere[:, :, 1] = atmosphere[1] * (1 - T)
        img_atmosphere[:, :, 2] = atmosphere[2] * (1 - T)

        hazy_img_like = np.zeros_like(clear_img)
        T = np.resize(T, np.shape(clear_img[:, :, 0]))
        hazy_img_like[:, :, 0] = (clear_img[:, :, 0] * T) + img_atmosphere[:, :, 0]
        hazy_img_like[:, :, 1] = (clear_img[:, :, 1] * T) + img_atmosphere[:, :, 1]
        hazy_img_like[:, :, 2] = (clear_img[:, :, 2] * T) + img_atmosphere[:, :, 2]

        img_a = cv2.normalize(hazy_img_like, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)
        transmission_img = cv2.resize(T, self.resize_shape)

        #img_atmosphere = self.initial_img_op(img_atmosphere)

        if(self.should_crop):
            crop_indices = transforms.RandomCrop.get_params(img_a, output_size=self.crop_size)
            i, j, h, w = crop_indices

            img_a = transforms.functional.crop(img_a, i, j, h, w)
            #img_b = transforms.functional.crop(img_b, i, j, h, w)
            #img_a = img_a[i: i + h, j: j + w]
            transmission_img = transmission_img[i: i + h, j: j + w]
            img_atmosphere = img_atmosphere[i: i + h, j: j + w]
            clear_img_uint = clear_img_uint[i: i + h, j: j + w]


        img_a = self.final_transform_op(img_a)
        transmission_img = self.depth_transform_op(transmission_img)
        img_atmosphere = self.final_transform_op(img_atmosphere)

        if(self.return_ground_truth):
            ground_truth_img = self.final_transform_op(clear_img_uint)
            return file_name, img_a, transmission_img, ground_truth_img, img_atmosphere
        else:
            return file_name, img_a, transmission_img, img_atmosphere #hazy albedo img, transmission map

    def __len__(self):
        return len(self.image_list_a)

class TransmissionAlbedoDatasetTest(data.Dataset):
    def __init__(self, image_list_a):
        self.image_list_a = image_list_a

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 256))
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        img_a = cv2.imread(img_id);
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        img_a = cv2.normalize(img_a, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)
        img_a = self.final_transform_op(img_a)

        return file_name, img_a

    def __len__(self):
        return len(self.image_list_a)

class AirlightDataset(data.Dataset):
    ATMOSPHERE_MIN = 0.3
    ATMOSPHERE_MAX = 0.95
    #ATMOSPHERE_MIN = 0.35
    #ATMOSPHERE_MAX = 1.0

    @staticmethod
    def atmosphere_mean():
        return (AirlightDataset.ATMOSPHERE_MIN + AirlightDataset.ATMOSPHERE_MAX) / 2.0;

    @staticmethod
    def atmosphere_std():
        return math.sqrt(pow(AirlightDataset.ATMOSPHERE_MAX - AirlightDataset.ATMOSPHERE_MIN, 2) / 12)

    def __init__(self, image_list_a, depth_dir, crop_size, should_crop, return_ground_truth):
        self.image_list_a = image_list_a
        self.depth_dir = depth_dir
        self.crop_size = crop_size
        self.should_crop = should_crop
        self.return_ground_truth = return_ground_truth
        self.resize_shape = (256, 256)

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(self.resize_shape)
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            #kornia.color.RgbToHsv(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

        self.depth_transform_op = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        clear_img = cv2.imread(img_id);
        clear_img = cv2.cvtColor(clear_img, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        clear_img = cv2.resize(clear_img, self.resize_shape)
        clear_img_uint = clear_img
        clear_img = cv2.normalize(clear_img, dst=None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        img_id = self.depth_dir + file_name
        transmission_img = cv2.imread(img_id)
        transmission_img = cv2.cvtColor(transmission_img, cv2.COLOR_BGR2GRAY)
        transmission_img = cv2.resize(transmission_img, np.shape(clear_img[:, :, 0]))
        transmission_img = cv2.normalize(transmission_img, dst=None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        T = dehazing_proper.generate_transmission(1 - transmission_img, np.random.uniform(0.7, 0.95))  # also include clear samples

        # formulate hazy img
        atmosphere = [0.0, 0.0, 0.0]
        spread = 0.125
        atmosphere[0] = np.random.uniform(AirlightDataset.ATMOSPHERE_MIN, AirlightDataset.ATMOSPHERE_MAX)
        atmosphere[1] = np.random.normal(atmosphere[0], spread)  # randomize by gaussian on other channels using R channel atmosphere
        atmosphere[2] = np.random.normal(atmosphere[0], spread)

        img_atmosphere = np.zeros_like(clear_img)
        img_atmosphere[:, :, 0] = atmosphere[0] * (1 - T)
        img_atmosphere[:, :, 1] = atmosphere[1] * (1 - T)
        img_atmosphere[:, :, 2] = atmosphere[2] * (1 - T)

        hazy_img_like = np.zeros_like(clear_img)
        T = np.resize(T, np.shape(clear_img[:, :, 0]))
        hazy_img_like[:, :, 0] = (clear_img[:, :, 0] * T) + img_atmosphere[:, :, 0]
        hazy_img_like[:, :, 1] = (clear_img[:, :, 1] * T) + img_atmosphere[:, :, 1]
        hazy_img_like[:, :, 2] = (clear_img[:, :, 2] * T) + img_atmosphere[:, :, 2]

        img_a = cv2.normalize(hazy_img_like, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)

        transmission_img = cv2.resize(T, self.resize_shape)

        if (self.should_crop):
            crop_indices = transforms.RandomCrop.get_params(img_a, output_size=self.crop_size)
            i, j, h, w = crop_indices

            img_a = transforms.functional.crop(img_a, i, j, h, w)
            hazy_img_like = hazy_img_like[i: i + h, j: j + w]
            transmission_img = transmission_img[i: i + h, j: j + w]
            img_atmosphere = img_atmosphere[i: i + h, j: j + w]
            clear_img_uint = clear_img_uint[i: i + h, j: j + w]

        img_a = self.final_transform_op(hazy_img_like)
        transmission_img = self.depth_transform_op(transmission_img)
        img_atmosphere = self.final_transform_op(img_atmosphere)

        if (self.return_ground_truth):
            ground_truth_img = self.final_transform_op(clear_img_uint)
            return file_name, img_a, transmission_img, ground_truth_img, img_atmosphere
        else:
            return file_name, img_a, transmission_img, img_atmosphere  # hazy albedo img, transmission map

    def __len__(self):
        return len(self.image_list_a)

class AirlightDatasetTest(data.Dataset):
    def __init__(self, image_list_a):
        self.image_list_a = image_list_a

        self.initial_img_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 256))
        ])

        self.final_transform_op = transforms.Compose([
            transforms.ToTensor(),
            #kornia.color.RgbToHsv(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        img_a = cv2.imread(img_id);
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR
        img_a = cv2.normalize(img_a, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        img_a = self.initial_img_op(img_a)
        img_a = self.final_transform_op(img_a)

        return file_name, img_a

    def __len__(self):
        return len(self.image_list_a)

class ColorTransferDataset(data.Dataset):
    def __init__(self, image_list_a, image_list_b):
        self.image_list_a = image_list_a
        self.image_list_b = image_list_b
        
        self.final_transform_op = transforms.Compose([
                                    transforms.ToPILImage(),
                                    transforms.Resize((256, 256)),
                                    transforms.RandomCrop(constants.PATCH_IMAGE_SIZE),
                                    transforms.RandomVerticalFlip(),
                                    transforms.RandomHorizontalFlip(),
                                    transforms.ToTensor(),
                                    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
                                    ])
        
        
    
    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]
        
        img_a = cv2.imread(img_id); img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB) #because matplot uses RGB, openCV is BGR
        
        img_id = self.image_list_b[idx]
        img_b = cv2.imread(img_id); img_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB)
        
        img_a = self.final_transform_op(img_a)
        img_b = self.final_transform_op(img_b)
            
        return file_name, img_a, img_b
    
    def __len__(self):
        return len(self.image_list_a)


class ColorTransferTestDataset(data.Dataset):
    def __init__(self, img_list_a, img_list_b):
        self.img_list_a = img_list_a
        self.img_list_b = img_list_b

        self.final_transform_op = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(constants.TEST_IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

    def __getitem__(self, idx):
        img_id = self.img_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        img_a = cv2.imread(img_id);
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR

        img_id = self.img_list_b[idx]
        img_b = cv2.imread(img_id);
        img_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB)

        img_a = self.final_transform_op(img_a)
        img_b = self.final_transform_op(img_b)

        return file_name, img_a, img_b

    def __len__(self):
        return len(self.img_list_a)

class ColorAlbedoDataset(data.Dataset):
    def __init__(self, image_list_a, image_list_b, depth_dir):
        self.image_list_a = image_list_a
        self.image_list_b = image_list_b
        self.depth_dir = depth_dir

        self.final_transform_op = transforms.Compose([transforms.ToPILImage(),
                                                      transforms.Resize(constants.PATCH_IMAGE_SIZE),
                                                      transforms.ToTensor(),
                                                      transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])


    def __getitem__(self, idx):
        img_id = self.image_list_a[idx]
        path_segment = img_id.split("/")
        file_name = path_segment[len(path_segment) - 1]

        initial_img = cv2.imread(img_id);
        initial_img = cv2.cvtColor(initial_img, cv2.COLOR_BGR2RGB)  # because matplot uses RGB, openCV is BGR

        img_id = self.image_list_b[idx]
        img_b = cv2.imread(img_id);
        img_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB)

        img_a = self.final_transform_op(initial_img)
        img_b = self.final_transform_op(img_b)

        hazy_img = img_a
        return file_name, hazy_img, img_b

    def __len__(self):
        return len(self.image_list_a)