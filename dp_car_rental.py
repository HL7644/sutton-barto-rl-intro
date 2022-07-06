# -*- coding: utf-8 -*-
"""DP: Car Rental

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1X-1QcWoZk_dzndqXUaXQJWBkKW8NqMvl
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

torch.manual_seed(0)

def poisson(lambd, max): #return random number according to poisson distribution
  prob=[]
  if max<0:
    max=0
  for n in range(max+1):
    n_fact=np.math.factorial(n)
    prob_n=lambd**n*np.exp(-lambd)/n_fact
    prob.append(prob_n)
  prob=torch.FloatTensor(prob)
  sum=torch.sum(prob)
  prob=prob/sum #normalized probability of poisson distribution
  return prob

def get_avail_action(N, actions):
  list1=[]
  for loc1 in range(N+1):
    list2=[]
    for loc2 in range(N+1):
      state=[loc1, loc2]
      avail_action=[]
      for idx, action in enumerate(actions):
        if (state[0]+action[0])>=0 and (state[0]+action[0])<=N and (state[1]+action[1])>=0 and (state[1]+action[1])<=N:
          avail_action.append(action)
      list2.append(torch.LongTensor(avail_action))
    list1.append(list2)

  return list1

class rental():
  def __init__(self):
    self.N=10
    self.state_value=torch.randint(low=0, high=self.N+1, size=(self.N+1, self.N+1)) #max N cars at each location-> (N+1)^2 states
    self.policy=torch.zeros(self.N+1, self.N+1) #index within each available actions
    #self.policy=torch.randint(low=0, high=self.N+1, size=(self.N+1, self.N+1)) #deterministic: index 
    self.action_list=[0,1,2,3,4,5] #6 type of qty -> 11types of action
    self.actions=[]
    for qty in self.action_list:
      if qty==0:
        self.actions.append([qty,qty])
      else:
        self.actions.append([-qty,qty])
        self.actions.append([qty,-qty])
    self.avail_actions_list=get_avail_action(self.N, self.actions)
    self.dynamics_list=[]
    self.gamma=0.9
    self.lambda_req1=3
    self.lambda_req2=4
    self.lambda_ret1=3
    self.lambda_ret2=2
    #get possible actions for each state

    for loc1 in range(self.N+1):
      temp_list1=[]
      for loc2 in range(self.N+1):
        temp_list2=[]
        state=[loc1, loc2]
        avail_actions=self.avail_actions_list[loc1][loc2]
        for idx, action in enumerate(avail_actions):
          temp_list2.append(self.dynamics(state, action))
        temp_list1.append(temp_list2)
      self.dynamics_list.append(temp_list1)

  def dynamics(self, state, action): #p(s',r|s,a), a is an element of A(s)
    state_f_tensor=torch.zeros(self.N+1, self.N+1, 2)
    count=torch.zeros(self.N+1, self.N+1).long()
    mid_state=[state[0]+action[0], state[1]+action[1]]
    #state(end of day)->action->dynamics(return->request)->reward->state_f(end of day)
    return1=poisson(self.lambda_ret1, self.N-mid_state[0]) #returns not to exceed N cars
    return2=poisson(self.lambda_ret2, self.N-mid_state[1])
    request1=poisson(self.lambda_req1, mid_state[0])
    request2=poisson(self.lambda_req2, mid_state[1])
    #normalize probability s.t only valid returns have probability
    for ret1, ret1_prob in enumerate(return1):
      for ret2, ret2_prob in enumerate(return2):
        for req1, req1_prob in enumerate(request1):
          for req2, req2_prob in enumerate(request2):
            state_f=[mid_state[0]+ret1-req1, mid_state[1]+ret2-req2]
            count[state_f[0],state_f[1]]+=1
            reward=10*(req1+req2)-2*np.abs(action[0])
            probability=ret1_prob*ret2_prob*req1_prob*req2_prob
            #update average reward
            #Q(n+1)=Q(n)+(R(n)-Q(n))/n: average reward of each state
            state_f_tensor[state_f[0],state_f[1],0]+=(reward-state_f_tensor[state_f[0],state_f[1],0])/count[state_f[0],state_f[1]]
            state_f_tensor[state_f[0],state_f[1],1]+=probability

    return state_f_tensor
     
  def evaluation(self): #using policy iteration
    error=1
    thresh=1
    while error>=thresh:
      error=0
      for loc1 in range(self.N+1):
        for loc2 in range(self.N+1):
          v=self.state_value.detach().clone()[loc1, loc2]
          action_idx=int(self.policy[loc1, loc2])
          state_f_tensor=self.dynamics_list[loc1][loc2][action_idx]
          temp=0
          for s1 in range(self.N+1):
            for s2 in range(self.N+1):
              reward=state_f_tensor[s1,s2,0]
              probability=state_f_tensor[s1,s2,1]
              temp+=probability*(reward+self.gamma*self.state_value[s1, s2])
          self.state_value[loc1, loc2]=temp
          error=max(error, np.abs(v-temp))
    return self.state_value

  def improvement(self): #using greedy w.r.t current state_value ftn
    policy_stable=True
    previous=self.policy.detach().clone()
    for loc1 in range(self.N+1):
      for loc2 in range(self.N+1):
        old_action_idx=previous[loc1, loc2]
        old_state_value=self.state_value[loc1, loc2]
        actions_per_state=self.avail_actions_list[loc1][loc2]
        improv_tensor=torch.zeros(len(actions_per_state))
        for idx, action in enumerate(actions_per_state):
          temp=0
          state_f_tensor=self.dynamics_list[loc1][loc2][idx]
          for s1 in range(self.N+1):
            for s2 in range(self.N+1):
              reward=state_f_tensor[s1,s2,0]
              probability=state_f_tensor[s1,s2,1]
              temp+=probability*(reward+self.gamma*self.state_value[s1,s2])
          improv_tensor[idx]=temp
        new_state_value, new_action_idx=torch.max(improv_tensor, dim=0)
        if new_action_idx != old_action_idx and new_state_value>old_state_value:
          self.policy[loc1, loc2]=new_action_idx
          policy_stable=False
    return policy_stable

car_rental=rental()
policy_stable=False
while policy_stable==False:
  state_value=car_rental.evaluation()
  policy_stable=car_rental.improvement()
print(state_value)
print(car_rental.policy)