# -*- coding: utf-8 -*-
"""Planning: DynaQ Maze

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1sVMHohiVe-IICUk1pZWrvXO1b5-I0FI8
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

def get_states(grid):
  h,w=grid.size()
  states=[]
  for row in range(h):
    for col in range(w):
      states.append([row,col])
  return states

class Maze():
  def __init__(self):
    #grid info
    self.grid=torch.zeros(6,9)
    self.h, self.w=self.grid.size()
    self.start=[5,3]
    self.goal=[0,8]
    self.states=get_states(self.grid)
    self.len_s=len(self.states)
    self.s_idx_list=np.arange(0,self.len_s,1)
    self.start_idx=self.find_s_idx(self.start)
    self.goal_idx=self.find_s_idx(self.goal)
    self.wall_1=[[3,0],[3,1],[3,2],[3,3],[3,4],[3,5],[3,6],[3,7]]
    self.wall_2=[[3,1],[3,2],[3,3],[3,4],[3,5],[3,6],[3,7],[3,8]]
    #actions info
    self.actions=[[-1,0],[1,0],[0,-1],[0,1]] #up, down, left, right
    self.len_a=len(self.actions)
    #model
    self.model=torch.zeros(self.len_s, self.len_a, 2) #last dim-> 0: s_idx_f, 1: reward
    #values
    self.action_value=torch.zeros(self.len_s, self.len_a)
    self.unselec_time=torch.zeros(self.len_s, self.len_a)
    #iteration info
    self.steps=1000
    self.n_planning=50
    self.gamma=.95
    self.kappa=0.0005 #coefficient for Dyna-Q+
    self.epsilon=0.4
    self.step_size=0.1
    self.n=3

  def find_s_idx(self, state):
    for s_idx, st in enumerate(self.states):
      if st[0]==state[0] and st[1]==state[1]:
        return s_idx

  def get_avail_actions(self, s_idx, step): #avail action indices for state
    avail_actions_idx=[]
    state=self.states[s_idx]
    for a_idx, action in enumerate(self.actions):
      state_f=[state[0]+action[0],state[1]+action[1]]
      s_idx_f=self.find_s_idx(state_f)
      if state[0]+action[0]>=0 and state[0]+action[0]<self.h and state[1]+action[1]>=0 and state[1]+action[1]<self.w:
        if self.check_wall(s_idx_f, step)==False:
          avail_actions_idx.append(a_idx)
    return avail_actions_idx
  
  def e_greedy_selection(self, s_idx, plus, step):
    avail_actions=self.get_avail_actions(s_idx, step)
    len_av=len(avail_actions)
    a_idx_list=[] #list of avail action index
    selection=[self.epsilon/len_av]*len_av
    temp=torch.zeros(len_av)
    for idx, a_idx in enumerate(avail_actions):
      if plus:
        temp[idx]=self.action_value[s_idx, a_idx]+self.kappa*torch.sqrt(self.unselec_time[s_idx, a_idx])
      else:
        temp[idx]=self.action_value[s_idx, a_idx]
      a_idx_list.append(a_idx)
    argmax_idx=torch.argmax(temp, dim=0)
    selection[argmax_idx]+=(1-self.epsilon)
    a_idx=random.choices(a_idx_list, selection)[0]
    return a_idx

  def greedy_selection(self, s_idx, step):
    avail_actions=self.get_avail_actions(s_idx, step)
    len_av=len(avail_actions)
    if len_av==0:
      print(self.states[s_idx])
    temp=torch.zeros(len_av)
    for idx, a_idx in enumerate(avail_actions):
      temp[idx]=self.action_value[s_idx, a_idx]
    argmax_idx=torch.argmax(temp, dim=0)
    a_idx=avail_actions[argmax_idx]
    return a_idx

  def check_wall(self, s_idx_f, step): #changing environment, True if s_idx_f intersects with wall
    state_f=self.states[s_idx_f]
    if step>1000:
      wall=self.wall_2
    else:
      wall=self.wall_1
    return_val=False
    for w in wall:
      if state_f[0]==w[0] and state_f[1]==w[1]:
        return_val=True
        break
    return return_val
      
  def transition(self, s_idx, a_idx, step):
    state=self.states[s_idx]
    action=self.actions[a_idx]
    state_f=[state[0]+action[0], state[1]+action[1]]
    s_idx_f=self.find_s_idx(state_f)
    if s_idx_f==self.goal_idx:
      reward=1
      termination=True
      s_idx_f=self.start_idx
    else:
      reward=0
      termination=False
    return s_idx_f, reward, termination
  
  def list_component(self, target_list, component): #returns true if component is in the list
    return_val=False
    for element in target_list:
      if element[0]==component[0] and element[1]==component[1]:
        return_val=True
        break
    return return_val

  def dyna_q(self, plus_rew=False, plus_act=False):
    p_thresh=0.5
    Queue=torch.Tensor([])
    grid=torch.zeros(6,9)
    self.action_value=torch.zeros(self.len_s, self.len_a)
    self.unselec_time=torch.zeros(self.len_s, self.len_a)
    s_idx=self.start_idx
    cumul_reward_list=[]
    cumul_reward_list.append(0)
    experience_sa=[]
    for step in range(self.steps):
      st=self.states[s_idx]
      grid[st[0],st[1]]+=1
      a_idx=self.e_greedy_selection(s_idx, plus_act, step)
      if self.list_component(experience_sa, [s_idx, a_idx])==False:
        experience_sa.append([s_idx, a_idx])
      #transition
      s_idx_f, reward,_=self.transition(s_idx, a_idx, step)
      if plus_rew:
        reward+=self.kappa*torch.sqrt(self.unselec_time[s_idx, a_idx]).item()
      cumul_reward=cumul_reward_list[-1]+reward
      cumul_reward_list.append(cumul_reward) #R_(t+1)
      #model learning
      self.model[s_idx, a_idx, 0]=s_idx_f
      self.model[s_idx, a_idx, 1]=reward
      #direct RL
      a_idx_f=self.greedy_selection(s_idx_f, step)
      priority=torch.abs(reward+self.gamma*self.action_value[s_idx_f, a_idx_f]-self.action_value[s_idx, a_idx])
      if priority>p_thresh:
        Queue=torch.cat((Queue, torch.FloatTensor([[s_idx, a_idx, priority]])), dim=0)
        _,sorted_idx=torch.sort(Queue[:,2], dim=0)
        Queue=Queue[sorted_idx]
      self.action_value[s_idx, a_idx]+=self.step_size*(reward+self.gamma*self.action_value[s_idx_f, a_idx_f]-self.action_value[s_idx, a_idx])
      #update unselected time
      self.unselec_time+=1
      self.unselec_time[s_idx, a_idx]=0
      #update s_idx
      s_idx=s_idx_f
      #background planning
      for _ in range(self.n_planning):
        while len(Queue)!=0:
          sa=Queue[0]
          s_idx_p=sa[0].long()
          a_idx_p=sa[1].long()
          s_idx_f_p=self.model[s_idx, a_idx, 0].long()
          reward=self.model[s_idx_p, a_idx_p, 1]
          a_idx_f_p=self.greedy_selection(s_idx_f_p, step)
          self.action_value[s_idx_p, a_idx_p]+=self.step_size*(reward+self.gamma*self.action_value[s_idx_f_p, a_idx_f_p]-self.action_value[s_idx_p, a_idx_p])
          #Prioritized Sweeping
          #for all predecessor states
          for s_idx_bef in range(self.len_s):
            for a_idx_bef in range(self.len_a):
              if self.model[s_idx_bef, a_idx_bef, 0].long()==s_idx_p:
                reward=self.model[s_idx_bef, a_idx_bef, 1]
                a_idx_p=self.greedy_selection(s_idx_p, step)
                priority=torch.abs(reward+self.gamma*self.action_value[s_idx_p, a_idx_p]-self.action_value[s_idx_bef, a_idx_bef])
                if priority>p_thresh: 
                  Queue=torch.cat((Queue, torch.FloatTensor([[s_idx_bef, a_idx_bef, priority]])), dim=0)
                _,sorted_idx=torch.sort(Queue[:,2], dim=0)
                Queue=Queue[sorted_idx]
    return self.action_value, cumul_reward_list, grid

  def get_trajectory(self):
    ep_sidx=[]
    s_idx=self.start_idx
    ep_sidx.append(s_idx)
    step=0
    termination=False
    while termination==False:
      a_idx=self.greedy_selection(s_idx, step)
      s_idx_f, reward, termination=self.transition(s_idx, a_idx, step)
      if termination==False:
        ep_sidx.append(s_idx_f)
    ep_sidx.append(self.goal_idx)
    grid=self.grid.clone().detach()
    for idx in ep_sidx:
      st=self.states[idx]
      grid[st[0],st[1]]=1
    step+=1
    return grid

maze=Maze()
#av=maze.n_step_sarsa()
action_value1, cumul_reward_list1, g1=maze.dyna_q()
#action_value2, cumul_reward_list2, g2=maze.dyna_q(plus_rew=True, plus_act=False)
#action_value3, cumul_reward_list3, g3=maze.dyna_q(plus_rew=False, plus_act=True)
print(g1)

a=[]
a.append([4,5,6])
a.append([1,2,3])
a=np.sort(a, axis=-1)
print(a)

print(action_value1)

steps=np.arange(0,len(cumul_reward_list1),1)
plt.xticks(np.arange(0,len(steps),10000))
plt.plot(steps, cumul_reward_list1, 'r', label='Dyna-Q', linewidth=0.5)
plt.plot(steps, cumul_reward_list2, 'b', label='Bonus Reward', linewidth=0.5)
plt.plot(steps, cumul_reward_list3, 'k', label='Action Selection Bonus', linewidth=0.5)
plt.legend()