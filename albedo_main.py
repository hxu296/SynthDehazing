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
from trainers import albedo_trainer, early_stopper
import constants
     
parser = OptionParser()
parser.add_option('--server_config', type=int, help="Is running on COARE?", default=0)
parser.add_option('--cuda_device', type=str, help="CUDA Device?", default="cuda:0")
parser.add_option('--img_to_load', type=int, help="Image to load?", default=-1)
parser.add_option('--load_previous', type=int, help="Load previous?", default=0)
parser.add_option('--iteration', type=int, help="Style version?", default="1")
parser.add_option('--adv_weight', type=float, help="Weight", default="1.0")
parser.add_option('--likeness_weight', type=float, help="Weight", default="10.0")
parser.add_option('--psnr_loss_weight', type=float, help="Weight", default="0.0")
parser.add_option('--num_blocks', type=int, help="Num Blocks", default = 4)
parser.add_option('--use_psnr', type=int, help="LR", default="1")
parser.add_option('--batch_size', type=int, help="batch_size", default="512")
parser.add_option('--g_lr', type=float, help="LR", default="0.00002")
parser.add_option('--d_lr', type=float, help="LR", default="0.00002")
parser.add_option('--num_workers', type=int, help="Workers", default="12")
parser.add_option('--comments', type=str, help="comments for bookmarking", default = "FFA Net GAN. Paired learning for extracting albedo from a lit image and vice versa. \n"
                                                                                     "Uses BCE Loss for D(x).")

#--img_to_load=-1 --load_previous=1
#Update config if on COARE
def update_config(opts):
    constants.server_config = opts.server_config
    constants.ITERATION = str(opts.iteration)
    constants.TRANSMISSION_ESTIMATOR_CHECKPATH = 'checkpoint/' + constants.UNLIT_NETWORK_VERSION + "_" + constants.ITERATION + '.pt'
    
    if(constants.server_config == 1):
        print("Using COARE configuration. Workers: ", constants.num_workers, "Path: ", constants.TRANSMISSION_ESTIMATOR_CHECKPATH)

        constants.DATASET_CLEAN_PATH_COMPLETE_STYLED_3 = "/scratch1/scratch2/neil.delgallego/Synth Hazy 3/clean/"
        constants.DATASET_ALBEDO_PATH_COMPLETE_3 = "/scratch1/scratch2/neil.delgallego/Synth Hazy 3/albedo/"
        constants.DATASET_DEPTH_PATH_COMPLETE_3 = "/scratch1/scratch2/neil.delgallego/Synth Hazy 3/depth/"
        constants.DATASET_OHAZE_HAZY_PATH_COMPLETE = "/scratch1/scratch2/neil.delgallego/Hazy Dataset Benchmark/O-HAZE/hazy/"

        constants.DATASET_ALBEDO_PATH_PATCH_3 = "/scratch1/scratch2/neil.delgallego/Synth Hazy 3 - Patch/albedo/"
        constants.DATASET_ALBEDO_PATH_PSEUDO_PATCH_3 = "/scratch1/scratch2/neil.delgallego/Synth Hazy 3 - Patch/albedo - pseudo/"
        constants.DATASET_CLEAN_PATH_PATCH_STYLED_3 = "/scratch1/scratch2/neil.delgallego/Synth Hazy 3 - Patch/clean - styled/"

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
    
    trainer = albedo_trainer.AlbedoTrainer(device, opts.batch_size, opts.g_lr, opts.d_lr, opts.num_blocks)
    trainer.update_penalties(opts.adv_weight, opts.likeness_weight, opts.psnr_loss_weight, opts.use_psnr, opts.comments)
    early_stopper_l1 = early_stopper.EarlyStopper(30, early_stopper.EarlyStopperMethod.L1_TYPE, 2000)

    start_epoch = 0
    iteration = 0

    if(opts.load_previous): 
        checkpoint = torch.load(constants.UNLIT_NETWORK_CHECKPATH)
        start_epoch = checkpoint['epoch'] + 1   
        iteration = checkpoint['iteration'] + 1
        trainer.load_saved_state(checkpoint)
 
        print("Loaded checkpt: %s Current epoch: %d" % (constants.UNLIT_NETWORK_CHECKPATH, start_epoch))
        print("===================================================")
    
    # Create the dataloader
    train_loader = dataset_loader.load_color_albedo_train_dataset(constants.DATASET_CLEAN_PATH_COMPLETE_STYLED_4, constants.DATASET_ALBEDO_PATH_COMPLETE_4, opts)
    test_loader= dataset_loader.load_color_albedo_test_dataset(constants.DATASET_CLEAN_PATH_COMPLETE_STYLED_4, constants.DATASET_ALBEDO_PATH_COMPLETE_4, opts)
    index = 0

    # Plot some training images
    if (constants.server_config == 0):
        _, a, b = next(iter(train_loader))
        show_images(a, "Training - Clear Images")
        show_images(b, "Training - Albedo Images")
    
    print("Starting Training Loop...")
    for epoch in range(start_epoch, constants.num_epochs):
        # For each batch in the dataloader
        for i, (train_data, test_data) in enumerate(zip(train_loader, test_loader)):
            _, dirty_batch, clean_batch = train_data
            dirty_tensor = dirty_batch.to(device)
            clean_tensor = clean_batch.to(device)

            trainer.train(dirty_tensor, clean_tensor)
            clean_like = trainer.test(dirty_tensor)

            if(early_stopper_l1.test(trainer, epoch, iteration, clean_like, clean_tensor)):
                break

            if(i % 100 == 0):
                trainer.save_states_unstable(epoch, iteration)

                view_batch, view_dirty_batch, view_clean_batch = next(iter(test_loader))
                view_dirty_batch = view_dirty_batch.to(device)
                view_clean_batch = view_clean_batch.to(device)
                trainer.visdom_report(iteration, dirty_tensor, clean_tensor, view_dirty_batch, view_clean_batch)

                iteration = iteration + 1
                index = (index + 1) % len(test_loader)
                if(index == 0):
                    test_loader = dataset_loader.load_color_albedo_test_dataset(constants.DATASET_CLEAN_PATH_COMPLETE_STYLED_3, constants.DATASET_ALBEDO_PATH_COMPLETE_3, constants.DATASET_DEPTH_PATH_COMPLETE_3, opts)

            if (early_stopper_l1.test(trainer, epoch, iteration, clean_like, clean_tensor)):
                break


#FIX for broken pipe num_workers issue.
if __name__=="__main__": 
    main(sys.argv)

