# -*- coding: utf-8 -*-
"""TD: CliffWalking

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Gqay0a4_W-tb8gcEDnQ1GajOAnNDSxXx
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
  states=[]
  h,w=grid.size()
  for row in range(h):
    for col in range(w):
      states.append([row,col])
  return states

class cliff_walking():
  def __init__(self):
    #define grids and states
    self.grid=torch.zeros(4,12)
    self.states=get_states(self.grid)
    self.start=[3,0]
    self.goal=[3,11]
    self.cliff=[[3,1],[3,2],[3,3],[3,4],[3,5],[3,6],[3,7],[3,8],[3,9],[3,10]]
    self.cliff_indices=[]
    for cl in self.cliff:
      self.cliff_indices.append(self.find_s_idx(cl))
    self.start_idx=self.find_s_idx(self.start)
    self.goal_idx=self.find_s_idx(self.goal)
    self.len_s=len(self.states)
    #define actions
    self.action_list=[[-1,0],[1,0],[0,-1],[0,1]] #corresponding to up, down, left, right
    self.len_a=len(self.action_list)
    self.avail_actions_idx=self.get_avail_actions()
    #define values
    self.action_value_s=torch.zeros(self.len_s, self.len_a)
    self.action_value_q=torch.zeros(self.len_s, self.len_a)
    #iteration parameters
    self.iter=8000
    self.epsilon=0.1
    self.step_size=0.1

  def find_s_idx(self, state):
    for idx, st in enumerate(self.states):
      if st[0]==state[0] and st[1]==state[1]:
        return idx

  def get_avail_actions(self):
    av_actions_idx=[]
    for st in self.states:
      temp=[]
      for a_idx, act in enumerate(self.action_list):
        sf0=st[0]+act[0]
        sf1=st[1]+act[1]
        if sf0>=0 and sf1>=0 and sf0<4 and sf1<12:
          temp.append(a_idx)
      av_actions_idx.append(temp)
    return av_actions_idx

  def check_cliff(self, s_idx):
    ret=False
    for cl_idx in self.cliff_indices:
      if cl_idx==s_idx:
        ret=True
        break
    return ret
      
  def get_e_greedy_s(self, s_idx): #returns probability list for e-greedy for sarsa
    av_actions_idx=self.avail_actions_idx[s_idx]
    len_av=len(av_actions_idx)
    e_greedy=[self.epsilon/len_av]*len_av
    temp=torch.zeros(len_av)
    for idx,a_idx in enumerate(av_actions_idx):
      temp[idx]=self.action_value_s[s_idx, a_idx]
    argmax_idx=torch.argmax(temp, dim=0)
    e_greedy[argmax_idx]+=(1-self.epsilon)
    return e_greedy

  def get_e_greedy_q(self, s_idx): #returns probability list for e-greedy for Q
    av_actions_idx=self.avail_actions_idx[s_idx]
    len_av=len(av_actions_idx)
    e_greedy=[self.epsilon/len_av]*len_av
    temp=torch.zeros(len_av)
    for idx,a_idx in enumerate(av_actions_idx):
      temp[idx]=self.action_value_q[s_idx, a_idx]
    argmax_idx=torch.argmax(temp, dim=0)
    e_greedy[argmax_idx]+=(1-self.epsilon)
    return e_greedy
          
  def progression(self, s_idx, a_idx):
    state=self.states[s_idx]
    action=self.action_list[a_idx]
    sf0=state[0]+action[0]
    sf1=state[1]+action[1]
    state_f=[sf0, sf1]
    s_idx_f=self.find_s_idx(state_f)
    if self.check_cliff(s_idx_f):
      termination=False
      s_idx_f=self.start_idx #back to start
      reward=-100
    elif s_idx_f==self.goal_idx:
      termination=True
      reward=-1
    else:
      termination=False
      reward=-1
    return s_idx_f, reward, termination

  def sarsa(self):
    #measure performance
    avg_reward_list=[]
    avg_reward=0
    tot_count=0
    for epoch in range(1, self.iter+1):
      rew_temp=0
      s_idx=self.start_idx
      termination=False
      while termination==False:
        e_greedy=self.get_e_greedy_s(s_idx)
        av_actions_idx=self.avail_actions_idx[s_idx]
        a_idx=random.choices(av_actions_idx, e_greedy)[0]
        s_idx_f, reward, termination=self.progression(s_idx, a_idx)
        e_greedy_f=self.get_e_greedy_s(s_idx_f)
        av_actions_idx_f=self.avail_actions_idx[s_idx_f]
        a_idx_f=random.choices(av_actions_idx_f, e_greedy_f)[0]
        #sarsa update
        self.action_value_s[s_idx,a_idx]+=self.step_size*(reward+self.action_value_s[s_idx_f,a_idx_f]-self.action_value_s[s_idx,a_idx])
        s_idx=s_idx_f
        a_idx=a_idx_f
        #performance calculation
        rew_temp+=reward
      tot_count+=1
      avg_reward+=(rew_temp-avg_reward)/tot_count
      avg_reward_list.append(avg_reward)
    return self.action_value_s, avg_reward_list

  def q_learning(self):
    #measure performance
    avg_reward=0
    tot_count=0
    avg_reward_list=[]
    for epoch in range(1, self.iter+1):
      rew_temp=0
      s_idx=self.start_idx
      termination=False
      while termination==False:
        e_greedy=self.get_e_greedy_q(s_idx)
        av_actions_idx=self.avail_actions_idx[s_idx]
        a_idx=random.choices(av_actions_idx, e_greedy)[0]
        s_idx_f, reward, termination=self.progression(s_idx, a_idx)
        av_actions_idx_f=self.avail_actions_idx[s_idx_f]
        e_greedy_f=self.get_e_greedy_q(s_idx_f)
        argmax_idx=np.argmax(e_greedy_f)
        a_idx_f=av_actions_idx_f[argmax_idx] #take maximum value action index
        #q_learning update
        self.action_value_q[s_idx,a_idx]+=self.step_size*(reward+self.action_value_q[s_idx_f,a_idx_f]-self.action_value_q[s_idx,a_idx])
        s_idx=s_idx_f
        #performance calculation
        rew_temp+=reward
      tot_count+=1
      avg_reward+=(rew_temp-avg_reward)/tot_count
      avg_reward_list.append(avg_reward)

    return self.action_value_q, avg_reward_list

  def optimal_trajectories_s(self):
    state_list=[]
    s_idx=self.start_idx
    state_list.append(s_idx)
    termination=False
    while termination==False:
      #follow greedy w.r.t current action value
      s_idx=state_list[-1]
      e_greedy=self.get_e_greedy_s(s_idx)
      argmax_idx=np.argmax(e_greedy)
      av_actions_idx=self.avail_actions_idx[s_idx]
      a_idx=av_actions_idx[argmax_idx]
      s_idx_f,_,termination=self.progression(s_idx, a_idx)
      state_list.append(s_idx_f)
    grid=torch.zeros(4,12)
    for s_idx in state_list:
      state=self.states[s_idx]
      grid[state[0],state[1]]=1
    return grid
  
  def optimal_trajectories_q(self):
    state_list=[]
    s_idx=self.start_idx
    state_list.append(s_idx)
    termination=False
    while termination==False:
      #follow greedy w.r.t current action value
      s_idx=state_list[-1]
      e_greedy=self.get_e_greedy_q(s_idx)
      argmax_idx=np.argmax(e_greedy)
      av_actions_idx=self.avail_actions_idx[s_idx]
      a_idx=av_actions_idx[argmax_idx]
      s_idx_f,_,termination=self.progression(s_idx, a_idx)
      state_list.append(s_idx_f)
    grid=torch.zeros(4,12)
    for s_idx in state_list:
      state=self.states[s_idx]
      grid[state[0],state[1]]=1
    return grid

cliffwalking=cliff_walking()
av_s, sarsa_rewards=cliffwalking.sarsa()
av_q, q_rewards=cliffwalking.q_learning()
traj_s=cliffwalking.optimal_trajectories_s()
traj_q=cliffwalking.optimal_trajectories_q()

print(traj_s)
print(traj_q)

#plot performance
x_range=len(q_rewards)
x=np.arange(0,x_range,1)
plt.plot(x,sarsa_rewards, 'k',label='Sarsa',linewidth=1)
plt.plot(x,q_rewards, 'b',label='Q-Learning', linewidth=1)
plt.xlim((0,8200))
plt.yticks(np.arange(-100,0,10))
plt.ylim((-100,0))
plt.xlabel('Epoch')
plt.ylabel('Avg. of Sum of Rewards')
plt.title('Avg. of Sum of Rewards w.r.t Epoch')
plt.legend(loc='best')
plt.show()