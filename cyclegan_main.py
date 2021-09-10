# -*- coding: utf-8 -*-
"""
Main entry for GAN training
Created on Sun Apr 19 13:22:06 2020

@author: delgallegon
"""

from __future__ import print_function
import sys
from optparse import OptionParser
import random
import torch
import torch.nn.parallel
import torch.utils.data
import torchvision.utils as vutils
import numpy as np
import matplotlib.pyplot as plt
from loaders import dataset_loader
from trainers import cyclegan_trainer
import constants
     
parser = OptionParser()
parser.add_option('--server_config', type=int, help="Is running on COARE?", default=0)
parser.add_option('--cuda_device', type=str, help="CUDA Device?", default="cuda:0")
parser.add_option('--img_to_load', type=int, help="Image to load?", default=-1)
parser.add_option('--load_previous', type=int, help="Load previous?", default=0)
parser.add_option('--iteration', type=int, help="Style version?", default="1")
parser.add_option('--identity_weight', type=float, help="Weight", default="0.0")
parser.add_option('--adv_weight', type=float, help="Weight", default="1.0")
parser.add_option('--likeness_weight', type=float, help="Weight", default="1.0")
parser.add_option('--smoothness_weight', type=float, help="Weight", default="0.0")
parser.add_option('--cycle_weight', type=float, help="Weight", default="10.0")
parser.add_option('--num_blocks', type=int, help="", default="10")
parser.add_option('--g_lr', type=float, help="LR", default="0.0002")
parser.add_option('--d_lr', type=float, help="LR", default="0.0002")
parser.add_option('--t_min', type=float, help="", default="0.1")
parser.add_option('--t_max', type=float, help="", default="1.2")
parser.add_option('--a_min', type=float, help="", default="0.1")
parser.add_option('--a_max', type=float, help="", default="0.95")
parser.add_option('--batch_size', type=int, help="batch_size", default="128")
parser.add_option('--num_workers', type=int, help="Workers", default="12")
parser.add_option('--comments', type=str, help="comments for bookmarking", default = "Vanilla CycleGAN.")

#--img_to_load=-1 --load_previous=1
#Update config if on COARE
def update_config(opts):
    constants.server_config = opts.server_config
    constants.ITERATION = str(opts.iteration)
    constants.STYLE_TRANSFER_CHECKPATH = 'checkpoint/' + constants.STYLE_TRANSFER_VERSION + "_" + constants.ITERATION + '.pt'

    if(constants.server_config == 1):
        print("Using COARE configuration.")
        constants.ITERATION = str(opts.iteration)
        constants.STYLE_TRANSFER_CHECKPATH = 'checkpoint/' + constants.STYLE_TRANSFER_VERSION + "_" + constants.ITERATION + '.pt'

        constants.DATASET_PLACES_PATH = "/scratch1/scratch2/neil.delgallego/Places Dataset/"
        constants.DATASET_CLEAN_LOW_PATH = "/scratch1/scratch2/neil.delgallego/Synth Hazy - Low/clean/"
        constants.DATASET_DEPTH_LOW_PATH = "/scratch1/scratch2/neil.delgallego/Synth Hazy - Low/depth/"

def show_images(img_tensor, caption):
    device = torch.device("cuda:0" if (torch.cuda.is_available()) else "cpu")
    plt.figure(figsize=constants.FIG_SIZE)
    plt.axis("off")
    plt.title(caption)
    plt.imshow(np.transpose(vutils.make_grid(img_tensor.to(device)[:16], nrow = 8, padding=2, normalize=True).cpu(),(1,2,0)))
    plt.show()

def main(argv):
    (opts, args) = parser.parse_args(argv)
    update_config(opts)
    print(opts)
    print("=====================BEGIN============================")
    print("Server config? %d Has GPU available? %d Count: %d" % (constants.server_config, torch.cuda.is_available(), torch.cuda.device_count()))
    print("Torch CUDA version: %s" % torch.version.cuda)
    
    manualSeed = random.randint(1, 10000) # use if you want new results
    random.seed(manualSeed)
    torch.manual_seed(manualSeed)

    device = torch.device(opts.cuda_device if (torch.cuda.is_available()) else "cpu")
    print("Device: %s" % device)
    
    gt = cyclegan_trainer.CycleGANTrainer(device, opts.g_lr, opts.d_lr, opts.num_blocks)
    gt.update_penalties(opts.adv_weight, opts.identity_weight, opts.likeness_weight, opts.cycle_weight, opts.smoothness_weight, opts.comments)
    start_epoch = 0
    iteration = 0
    
    if(opts.load_previous):
        checkpoint = torch.load(constants.STYLE_TRANSFER_CHECKPATH)
        start_epoch = checkpoint['epoch'] + 1   
        iteration = checkpoint['iteration'] + 1
        gt.load_saved_state(checkpoint)
 
        print("Loaded checkpt: %s Current epoch: %d" % (constants.STYLE_TRANSFER_CHECKPATH, start_epoch))
        print("===================================================")
    
    # Create the dataloader
    train_loader = dataset_loader.load_color_train_dataset(constants.DATASET_CLEAN_PATH_COMPLETE_3, constants.DATASET_PLACES_PATH, opts)
    test_loader = dataset_loader.load_color_test_dataset(constants.DATASET_CLEAN_PATH_COMPLETE_3, constants.DATASET_PLACES_PATH, opts)
    index = 0
    
    # Plot some training images
    if(constants.server_config == 0):
        _, noisy_batch, clean_batch = next(iter(train_loader))

        show_images(noisy_batch, "Training - A Images")
        show_images(clean_batch, "Training - B Images")

    # for i, train_data in enumerate(train_loader, 0):
    #     _, dirty_batch, clean_batch = train_data
    #     dirty_tensor = dirty_batch.to(device)
    #     clean_tensor = clean_batch.to(device)
    #
    #     view_batch, view_dirty_batch, view_clean_batch = next(iter(test_loader))
    #     view_dirty_batch = view_dirty_batch.to(device)
    #     view_clean_batch = view_clean_batch.to(device)
    #     gt.visdom_report(iteration, dirty_tensor, clean_tensor, view_dirty_batch, view_clean_batch)
    #     break

    print("Starting Training Loop...")
    for epoch in range(start_epoch, constants.num_epochs):
        # For each batch in the dataloader
        for i, train_data in enumerate(train_loader, 0):
            _, dirty_batch, clean_batch = train_data
            dirty_tensor = dirty_batch.to(device)
            clean_tensor = clean_batch.to(device)

            gt.train(dirty_tensor, clean_tensor)
            if(i % 100 == 0):
                gt.save_states(epoch, iteration)
                # view_batch, view_dirty_batch, view_clean_batch = next(iter(test_loader_1))
                # view_dirty_batch = view_dirty_batch.to(device)
                # view_clean_batch = view_clean_batch.to(device)
                # gt.visdom_report(iteration, dirty_tensor, clean_tensor, view_dirty_batch, view_clean_batch)
                #
                # view_batch, view_dirty_batch, _ = next(iter(test_loader_2))
                # view_dirty_batch = view_dirty_batch.to(device)
                # gt.visdom_infer(view_dirty_batch, "O-Haze Hazy", "O-Haze Albedo")
                #
                # iteration = iteration + 1
                # index = (index + 1) % len(test_loader_1)
                # if(index == 0):
                #     test_loader_1 = dataset_loader.load_color_albedo_test_dataset(constants.DATASET_CLEAN_PATH_COMPLETE_STYLED_3, constants.DATASET_ALBEDO_PATH_COMPLETE_3, constants.DATASET_DEPTH_PATH_COMPLETE_3, constants.batch_size, 500)
                #     test_loader_2 = dataset_loader.load_color_albedo_test_dataset(constants.DATASET_OHAZE_HAZY_PATH_COMPLETE, constants.DATASET_ALBEDO_PATH_COMPLETE_3, None, constants.batch_size, 500)

#FIX for broken pipe num_workers issue.
if __name__=="__main__": 
    main(sys.argv)

