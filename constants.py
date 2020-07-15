# -*- coding: utf-8 -*-
import os

DATASET_VEMON_PATH = "E:/VEMON_Transfer/train/A/"
DATASET_GTA_PATH = "E:/VEMON_Transfer/train/B/"
DATASET_GTA_PATH_2= "E:/VEMON Dataset/pending/frames/"
DATASET_PLACES_PATH = "E:/Places Dataset/"
DATASET_DIV2K_PATH = "E:/VEMON_Transfer/train/C/"

BIRD_IMAGE_SIZE = (32, 32) #320 x 192 original
TEST_IMAGE_SIZE = (128, 128)
DIV2K_IMAGE_SIZE = (2040, 1404)
FIG_SIZE = (TEST_IMAGE_SIZE[0] / 2, TEST_IMAGE_SIZE[1] / 2)
TENSORBOARD_PATH = os.getcwd() + "/train_plot/"

#========================================================================#
OPTIMIZER_KEY = "optimizer"
GENERATOR_KEY = "generator"
DISCRIMINATOR_KEY = "discriminator"

STYLE_GAN_VERSION = "style_v1.03"
STYLE_ITERATION = "1"
STYLE_CHECKPATH = 'checkpoint/' + STYLE_GAN_VERSION + "_" + STYLE_ITERATION +'.pt'

# dictionary keys
G_LOSS_KEY = "g_loss"
IDENTITY_LOSS_KEY = "id"
CYCLE_LOSS_KEY = "cyc"
TV_LOSS_KEY = "tv"
G_ADV_LOSS_KEY = "g_adv"

D_OVERALL_LOSS_KEY = "d_loss"
D_A_REAL_LOSS_KEY = "d_real_a"
D_A_FAKE_LOSS_KEY = "d_fake_a"
D_B_REAL_LOSS_KEY = "d_real_b"
D_B_FAKE_LOSS_KEY = "d_fake_b"

# Set random seed for reproducibility
manualSeed = 999

# Number of training epochs
num_epochs = 500

test_display_size = 8
display_size = 16 #must not be larger than batch size
batch_size = 128
infer_size = 32

num_workers = 12

#Running on COARE?
is_coare = 0
    