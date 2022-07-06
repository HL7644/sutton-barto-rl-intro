# -*- coding: utf-8 -*-
"""RL: On-Policy Ftn. Approx.

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1WfEId1I-zGzNUaVoVPaXu2Y6gULvw8Qv
"""

import torch
import torch.optim as optim
import torch.nn.functional as F
import torch.nn as nn
import torchvision.datasets as dsets
import numpy as np
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import torchvision
import matplotlib.pyplot as plt
import random

import json
import pandas as pd
import os.path
import xml.etree.ElementTree as ET
import PIL
from google.colab import drive

torch.manual_seed(0)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

class interest_check():
  def __init__(self):
    self.weight=torch.zeros(1,2).to(device)
    self.states=torch.LongTensor([1,2,3,4]).to(device)
    #1st weight responsible for state 1,2 2nd for 3,4
    self.feature_vectors=torch.FloatTensor([[1,0],[1,0],[0,1],[0,1]]).to(device)
    self.interest=torch.FloatTensor([1,0,0,0]).to(device)
    self.len_s=self.states.size(0)
    #assume linear ftn. approximation
    self.value_ftn=torch.zeros(4).to(device)
  
  def progression(self, sidx):
    if sidx==3:
      sidx_f=sidx
      termination=True
      reward=1
    else:
      sidx_f=sidx+1
      reward=1
      termination=False
    return sidx_f, reward, termination

  def MC_gradient(self):
    step_size=1e-2
    iter=1000
    for epoch in range(1, iter+1):
      ep_sidx=[]
      ep_r=[]
      ep_r.append(0)
      #state initialization
      sidx=0
      ep_sidx.append(sidx)
      while True:
        sidx_f, reward, termination=self.progression(sidx)
        if termination:
          ep_r.append(reward)
          break
        else:
          ep_r.append(reward) #R_t+1
          ep_sidx.append(sidx_f) #S_t+1
          sidx=sidx_f
      ep_r.reverse()
      ep_sidx.reverse()
      target=0
      for idx, sidx in enumerate(ep_sidx):
        target+=ep_r[idx]
        #linear ftn approximator
        emphasis=self.interest[sidx]
        self.weight=self.weight+step_size*emphasis*(target-self.value_ftn[sidx])*self.feature_vectors[sidx]
        self.update()
      if epoch>0.9*iter:
        step_size=1e-5
      elif epoch>0.8*iter:
        step_size=1e-4
      elif epoch>0.7*iter:
        step_size=1e-3
    return self.weight
  
  def n_step_td(self):
    n=2
    step_size=1e-3
    iter=100000
    for epoch in range(1, iter+1):
      ep_sidx=[]
      ep_r=[]
      ep_r.append(0)
      sidx=0
      ep_sidx.append(sidx)
      ep_emphasis=[]
      step=0
      termin_step=np.inf
      while True:
        if step<termin_step:
          #for t
          if step-n>=0:
            emphasis=self.interest[sidx].item()+ep_emphasis[step-n]
          else:
            emphasis=self.interest[sidx].item()
          ep_emphasis.append(emphasis)
          #progression
          sidx_f, reward, termination=self.progression(sidx)
          ep_r.append(reward)
          #for t+1
          if termination:
            termin_step=step+1
          else:
            ep_sidx.append(sidx_f)
            sidx=sidx_f
        update_step=step-(n-1)
        if update_step>=0:
          n_step_return=0
          #iteration for t+1
          for t in range(update_step+1, min(update_step+n, termin_step)+1):
            n_step_return+=ep_r[t]
          if update_step+n<termin_step:
            n_step_return+=self.value_ftn[ep_sidx[update_step+n]]
          self.weight=self.weight+step_size*ep_emphasis[ep_sidx[update_step]]*(n_step_return-self.value_ftn[ep_sidx[update_step]])*self.feature_vectors[ep_sidx[update_step]]
          self.update()
        if update_step==termin_step-1:
          break
        else:
          step+=1
    return self.weight
 
  def update(self):
    for sidx in range(self.len_s):
      self.value_ftn[sidx]=self.weight.matmul(self.feature_vectors[sidx]).unsqueeze(dim=0).permute(1,0)

ic=interest_check()
weight=ic.n_step_td()
print(weight)