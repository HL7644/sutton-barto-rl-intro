# -*- coding: utf-8 -*-
"""MC: RaceTrack

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19WR8u5SsDiarUCWUrC3gAKFUVQ1a6nEh
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
from mpl_toolkits import mplot3d
import random

torch.manual_seed(0)

def get_boundaries1():
  boundaries=[[0,3],[0,4],[0,5],[0,6],[0,7],[0,8],[0,9],[0,10],[0,11],[0,12],[0,13],[0,14],[0,15],[0,16],[0,17],
              [1,3],[1,2],[2,2],[3,2],[3,1],[4,1],[4,0],[5,0],[6,0],[7,0],[8,0],[9,0],[10,0],[11,0],[12,0],[13,0],[14,0],[15,0],
              [15,1],[16,1],[17,1],[18,1],[19,1],[20,1],[21,1],[22,1],[23,1],[23,2],[24,2],[25,2],[26,2],[27,2],[28,2],[29,2],[30,2],
              [30,3],[31,3],[32,3],[32,10],[31,10],[30,10],[29,10],[28,10],[27,10],[26,10],[25,10],[24,10],[23,10],[22,10],[21,10],[20,10],
              [19,10],[18,10],[17,10],[16,10],[15,10],[14,10],[13,10],[12,10],[11,10],[10,10],[9,10],[8,10],[8,11],[7,11],[7,12],[7,13],[7,14],
              [7,15],[7,16],[7,17]]
  return boundaries

def label_grid(grid, boundaries, start_line, finish_line):
  for b in boundaries:
    grid[b[0],b[1]]=1
  for s in start_line:
    grid[s[0],s[1]]=2
  for f in finish_line:
    grid[f[0],f[1]]=3
  return grid

def get_state(grid, velocity):
  state=[]
  h,w=grid.size()
  for idx1 in range(h):
    for idx2 in range(w):
      for v_idx,_ in enumerate(velocity):
        state.append([idx1,idx2, v_idx])
  return state

def get_actions(action_list):
  actions=[]
  for a1 in action_list:
    for a2 in action_list:
      actions.append([a1,a2])
  return actions

def get_velocity():
  velocity=[]
  for row in range(5):
    for col in range(5):
      velocity.append([-row,col])
  return velocity

def init_action_value(state, len_s, len_a): #initialize action value only for available actions at each state
  action_value=torch.full((self.len_s, self.len_a),-100000) #fill w/ large negative integer to avoid being selected in argmax
  for s_idx, state in enumerate(self.state):
    avail_action=self.get_avail_action(state)
    for a_idx in avail_action:
      action_value[s_idx,a_idx]=np.random.randint(low=-10, high=0) #init available actions w/ relatively small negatives
  return action_value

def reverse_list(list_before):
  size=len(list_before)
  list_after=[]
  for idx in range(size):
    list_after.append(list_before[size-idx-1])
  return list_after

class RaceTrack1():
  def __init__(self):
    #set lines
    self.grid=torch.zeros(32+1,17+1)
    self.boundaries=get_boundaries1()
    self.start_line=[[32,4],[32,5],[32,6],[32,7],[32,8],[32,9]]
    self.finish_line=[[1,17],[2,17],[3,17],[4,17],[5,17],[6,17]]
    #define actions and velocities
    self.action_list=[-1,0,1]
    self.actions=get_actions(self.action_list)
    self.len_a=len(self.actions)
    #action index list
    self.a_idx_list=np.arange(0,self.len_a,1)
    self.velocity=get_velocity()
    #label boundaries as 1, start as 2, finish as 3
    self.grid=label_grid(self.grid, self.boundaries, self.start_line, self.finish_line)
    self.state=get_state(self.grid, self.velocity) #state: [row, col, v_idx]
    self.len_s=len(self.state)
    #cumulative ISR and action value
    self.cumulative_isr=torch.zeros(self.len_s, self.len_a)
    #initialize action value only for available actions at each state
    self.action_value=torch.full((self.len_s, self.len_a),-100000) #fill w/ large negative integer to avoid being selected in argmax
    for s_idx, state in enumerate(self.state):
      avail_action=self.get_avail_action(state)
      for a_idx in avail_action:
        self.action_value[s_idx,a_idx]=np.random.randint(low=-10, high=0) #init available actions w/ relatively small negatives
    #target & behavior
    self.target_policy=self.get_target_policy()
    self.behavior_policy=self.get_behav_policy()
    self.iter=100
  
  def get_target_policy(self): #deterministic policy greedy to action value
    policy=[]
    for s_idx, state in enumerate(self.state):
      avail_action=self.get_avail_action(state)
      temp=torch.zeros(self.len_a)
      for a_idx in avail_action:
        temp[a_idx]=self.action_value[s_idx,a_idx]
      argmax_idx=torch.argmax(temp, dim=0)
      policy.append(int(argmax_idx))
    return policy

  def get_behav_policy(self): #equiprobable between available actions
    b_policy=[]
    for s_idx,state in enumerate(self.state):
      avail_action=self.get_avail_action(state)
      len_av_a=len(avail_action)
      p=1/len_av_a
      action_temp=[0]*self.len_a
      for a_idx in avail_action:
        action_temp[a_idx]=p
      b_policy.append(action_temp)
    return b_policy

  def find_v_idx(self, velocity):
    for idx, v in enumerate(self.velocity):
      if v[0]==velocity[0] and v[1]==velocity[1]:
        return idx

  def find_state_idx(self, state):
    for idx, s in enumerate(self.state):
      if s[0]==state[0] and s[1]==state[1] and s[2]==state[2]:
        return idx

  def check_boundaries(self, current, state_f): #True if trajectory crosses boundary
    check=False #verify only w.r.t location
    for row in range(state_f[0], current[0]+1): #reverse order since moving upwards decreases row
      for col in range(current[1], state_f[1]+1):
        for bound in self.boundaries:
          if bound[0]==row and bound[1]==col:
            check=True
    return check

  def check_finish(self, current, state_f): #True if trajectory crosses finish line
    check=False #verify only w.r.t location
    for row in range(state_f[0], current[0]+1): #reverse order since moving upwards decreases row
      for col in range(current[1], state_f[1]+1):
        for fin in self.finish_line:
          if fin[0]==row and fin[1]==col:
            check=True
    return check

  def get_avail_action(self, state):
    avail_idx=[]
    row=state[0]
    col=state[1]
    v_idx=state[2]
    velocity=self.velocity[v_idx]
    for idx, a in enumerate(self.actions):
      vf0=a[0]+velocity[0] #upwards velocity: supposed to be negative
      vf1=a[1]+velocity[1]
      if vf0<=-5 or vf1>=5 or vf0>0 or vf1<0:
        continue
      elif vf0==0 and vf1==0:
        continue
      else:
        avail_idx.append(idx)
    return avail_idx

  def progression(self, s_idx, a_idx, velocity):
    current=self.state[s_idx]
    action=self.actions[a_idx]
    velocity_f=[velocity[0]+action[0], velocity[1]+action[1]]
    v_idx_f=self.find_v_idx(velocity_f)
    state_f=[current[0]+velocity_f[0], current[1]+velocity_f[1],v_idx_f]
    if self.check_boundaries(current, state_f)==True: #cross boundary
      reward=-1
      #move to start line
      loc_f=random.choice(self.start_line)
      velocity_f=[0,0]
      v_idx_f=self.find_v_idx(velocity_f)
      state_f=[loc_f[0],loc_f[1],v_idx_f]
      s_idx_f=self.find_state_idx(state_f)
      termination=False
    elif self.check_finish(current, state_f)==True: #cross finish line
      reward=-1
      s_idx_f=s_idx
      termination=True
    else: #normal action
      reward=-1
      termination=False
      s_idx_f=self.find_state_idx(state_f)
    return s_idx_f, velocity_f, reward, termination

  def episode_generator(self):
    velocity=[0,0] #idx0 for downwards, idx1 for rightwards
    episode_state=[]
    episode_action=[]
    episode_reward=[]
    start=random.choice(self.start_line)
    v_idx=self.find_v_idx(velocity)
    start_state=[start[0],start[1],v_idx]
    start_idx=self.find_state_idx(start_state)
    episode_state.append(start_idx)
    avail_a_idx=self.get_avail_action(start_state)
    episode_action.append(random.choice(avail_a_idx))
    termination=False
    while(termination==False):
      s_idx=episode_state[-1]
      a_idx=episode_action[-1]
      s_idx_f, velocity, reward, termination=self.progression(s_idx, a_idx, velocity)
      episode_reward.append(reward)
      if termination==False:
        episode_state.append(s_idx_f)
        a_prob_distribution=self.behavior_policy[s_idx_f] #probability distribution of actions
        a_idx_f=random.choices(self.a_idx_list, a_prob_distribution)
        episode_action.append(int(a_idx_f[0]))
    return episode_state, episode_action, episode_reward
  
  def evaluation(self):
    for epoch in range(1, self.iter+1):
      ep_s, ep_a, ep_r=self.episode_generator()
      ep_s=reverse_list(ep_s)
      ep_a=reverse_list(ep_a)
      ep_r=reverse_list(ep_r)
      returns=0
      isr=1
      for idx, s_idx in enumerate(ep_s):
        a_idx=ep_a[idx]
        reward=ep_r[idx]
        returns+=reward
        self.cumulative_isr[s_idx,a_idx]+=isr
        self.action_value[s_idx,a_idx]=self.action_value[s_idx,a_idx]+isr*(returns-self.action_value[s_idx,a_idx])/self.cumulative_isr[s_idx,a_idx]
        #determine greedy action
        temp=torch.zeros(self.len_a)
        for idx in range(self.len_a):
          temp[idx]=self.action_value[s_idx,idx].detach().clone()
        self.target_policy[s_idx]=torch.argmax(temp, dim=0)
        if self.target_policy[s_idx]!=a_idx:
          break
        prob_of_action_b=self.behavior_policy[s_idx][a_idx]
        isr=isr/prob_of_action_b
    return self.action_value

track1=RaceTrack1()
av_init=track1.action_value.detach().clone()
action_value=track1.evaluation()

print(torch.sum(av_init))
print(torch.sum(action_value))