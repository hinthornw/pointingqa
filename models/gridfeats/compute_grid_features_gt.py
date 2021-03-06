# Computes grid features within ground truth bounding box around point

import torch
import json
import numpy as np
import math
import os
import argparse

# Iterate through images from low to high (used to parallelize)																		
parser = argparse.ArgumentParser()
parser.add_argument('--lower', type=int)
parser.add_argument('--higher', type=int)
args = parser.parse_args()

with open('', 'r') as f:
     dataset = json.load(f)

grid_dir = './gridfeats/'
size_dir = './img_sizes/'
out_dir = './gridfeats_gt/'

img_ids = list(dataset.keys())

cnt = 0
feat_cnt = []
for img_id in img_ids[args.lower:args.higher]:
     cnt += 1
     if cnt % 100 == 0:
	  print(cnt)

     # Read in grid features
     grid_path = grid_dir + str(img_id) + '.pt'
     grid_img = torch.load(grid_path).squeeze()
     gridh, gridw = grid_img.shape[1:]
     
     # Read in imge size
     size_path = size_dir + str(img_id) + '.npy'
     size_img = np.load(size_path)
     h, w = size_img[0], size_img[1]
     
     min_size = min(w, h)
     max_size = max(w, h)

     # compute image scale factor
     img_scale = 600 / min_size
     if img_scale * max_size > 1000:
	  img_scale = 1000 / max_size

     neww = int(w * img_scale + 0.5)
     newh = int(h * img_scale + 0.5)

     wmod = neww % 32
     hmod = newh % 32
     
     if wmod != 0:
	  neww += (32 - wmod)
     
     if hmod != 0:
	  newh += (32 - hmod) 

     for qa in dataset[img_id]:
	  for obj in qa['all_objs']:
	       # x, y = pt['x'], pt['y']
	       
	       # if os.path.exists(fname): continue
	       
	       xmin, xmax = obj['x'], obj['x'] + obj['w']
	       ymin, ymax = obj['y'], obj['y'] + obj['h']

	       # rescale bbox
	       new_xmin, new_xmax = xmin * (neww/w), xmax * (neww/w)
	       new_ymin, new_ymax = ymin * (newh/h), ymax * (newh/h)
	       
	       # downsample point
	       down_xmin, down_xmax = int(math.floor(new_xmin / 32)), int(math.floor(new_xmax / 32))
	       down_ymin, down_ymax = int(math.floor(new_ymin / 32)), int(math.floor(new_ymax / 32))
	  
	       grid_feat = grid_img[:, down_ymin:down_ymax+1, down_xmin:down_xmax+1]
	       grid_feat = grid_feat.reshape(grid_feat.shape[0], -1).T
	       feat_cnt.append(grid_feat.shape[0])

	       x = int(math.floor(obj['x'] + 0.5 * obj['w']))
	       y = int(math.floor(obj['y'] + 0.5 * obj['h']))

	       fname = out_dir + str(img_id) + ',' + str(x) + ',' + str(y) + '.pt'

	       torch.save(grid_feat, fname)

print(max(feat_cnt))
np.save('featcnt' + str(args.lower), np.array(feat_cnt))
