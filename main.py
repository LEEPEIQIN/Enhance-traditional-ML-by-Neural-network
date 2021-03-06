import os
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import random
import sklearn
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn import preprocessing
from sklearn.model_selection import KFold
from sklearn.ensemble import AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
import torch
from torch import nn
import torch.optim as optim
from sklearn.pipeline import make_pipeline
from genetic_selection import GeneticSelectionCV
import math
import copy
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import BaggingClassifier
from torch.utils.data import Dataset, DataLoader, TensorDataset





data=pd.read_csv('adult.csv')
#which column is categorical and which is numerical
categorical_index=[0,1, 2, 3, 4, 5, 6, 7 ]
numerical_index=[8,9,10,11,12,13]
for i in data.columns[categorical_index]:
    data.loc[:,i]=data.loc[:,i].astype('category')
    
X=data.iloc[:,0:(len(categorical_index)+len(numerical_index))]
Y=data.iloc[:,len(categorical_index)+len(numerical_index)]
#identify which feature used to seperate dataset
name=X.columns[6]
#identify method used
method=XGBClassifier(random_state=42)
#method=GradientBoostingClassifier(random_state=42)
#method=RandomForestClassifier(random_state=42)
#method=DecisionTreeClassifier(criterion='gini',random_state=42)
#method=LogisticRegression(random_state=42,max_iter=10000)
#method=SVC(kernel='linear',random_state=42,probability=True)
label=list(np.unique(Y))
#create threshold for minimum number of each iteration 
hold=120
cluster=X.loc[:,name]
levels=cluster.unique()
true_levels=[]
for n in levels:
     position=(cluster==n)
     y_temp=Y.loc[position].reset_index(drop=True)
     if len(y_temp)>=hold:
         true_levels=true_levels+[n]

#it is for featrue selection(if necessary)
feature_selection_categorical=list()    
for i in range(len(true_levels)+1):
    feature_selection_categorical.append([0,1,2,3,4,5,6,7])
    
feature_selection_continous=list()    
for i in range(len(true_levels)+1):
    feature_selection_continous.append([0,1,2,3,4,5])

#number of epoch for NN 
epoch=1000

#define NN
class dicision_kernel(nn.Module):
        def __init__(self):
            super(dicision_kernel, self).__init__()
            self.linear1=nn.Linear(6,2)
        def forward(self,x):
            x=x.reshape([x.size()[0],x.size()[1]*x.size()[2]])
            x=self.linear1(x)
            x=x.squeeze()
            x=torch.softmax(x,dim=1)
            return x  
####################################
Precision_0=np.zeros(len(label)+1)
Precision_refer=np.zeros([len(label)+1,len(true_levels)])
Precision_record=np.zeros([epoch])
Loss_record=np.zeros([epoch])

kf=KFold(n_splits=10,shuffle=True,random_state=10)
kf.get_n_splits(data)
for k in kf.split(data):
    models=list()
    for i in range(len(true_levels)+1):
        models.append(copy.copy(method))
    x_categorical=data.drop(k[1]).iloc[:,categorical_index].reset_index(drop=True)
    x_continuous=data.drop(k[1]).iloc[:,numerical_index].reset_index(drop=True)
    x_categorical_test=data.iloc[k[1],:].iloc[:,categorical_index].reset_index(drop=True)
    x_continuous_test=data.iloc[k[1],:].iloc[:,numerical_index].reset_index(drop=True)
    target=data.drop(k[1]).iloc[:,(len(categorical_index)+len(numerical_index))].reset_index(drop=True)
    target_test=data.iloc[k[1],(len(categorical_index)+len(numerical_index))].reset_index(drop=True)
        
    tensor_train=torch.FloatTensor(np.zeros([(len(true_levels)+1),len(label)]))
    tensor_train=tensor_train.repeat(len(target),1,1)
    tensor_test=torch.FloatTensor(np.zeros([(len(true_levels)+1),len(label)]))
    tensor_test=tensor_test.repeat(len(target_test),1,1)
    #predictor_0
    enc_1=preprocessing.OneHotEncoder()
    enc_1.fit(pd.concat([x_categorical,x_categorical_test]).iloc[:,feature_selection_categorical[0]])  
    
    train_x=pd.DataFrame(enc_1.transform(x_categorical.iloc[:,feature_selection_categorical[0]]).toarray()) 
    train_x=train_x.join(x_continuous.iloc[:,feature_selection_continous[0]])
    test_x=pd.DataFrame(enc_1.transform(x_categorical_test.iloc[:,feature_selection_categorical[0]]).toarray())
    test_x=test_x.join(x_continuous_test.iloc[:,feature_selection_continous[0]])
    
    predictor_0=models[0]
    predictor_0.fit(train_x,target)
    
    pred_0=predictor_0.predict_proba(train_x)
    tensor_train[:,0,:]=torch.FloatTensor(pred_0)
    pred_0=predictor_0.predict_proba(test_x)
    tensor_test[:,0,:]=torch.FloatTensor(pred_0)
    
    pred=predictor_0.predict(test_x)
    con=sklearn.metrics.confusion_matrix(target_test,pred,labels=label)
    precision=np.zeros(len(con)+1)
    t=0.0
    for i in range(len(con)):
        precision[i]=con[i,i]/sum(con[:,i])
        t+=con[i,i]
    precision[len(con)]=t/sum(sum(con))
    precision_0=copy.copy(precision) 
    
    #predictor_refer
    predictor_refer=models[1:(len(true_levels)+1)]
    precision_refer=np.zeros([len(true_levels),len(con)+1])
    for i in range(len(true_levels)):
        enc_set=preprocessing.OneHotEncoder()
        enc_set.fit(pd.concat([x_categorical,x_categorical_test]).iloc[:,feature_selection_categorical[i+1]])  
    
        cluster=x_categorical[name]
        position=(cluster==true_levels[i])
        train_x=pd.DataFrame(enc_set.transform(x_categorical.iloc[:,feature_selection_categorical[i+1]]).toarray())[position].reset_index(drop=True)
        train_x=train_x.join(x_continuous.iloc[:,feature_selection_continous[i+1]][position].reset_index(drop=True))
        train_y=target[position].reset_index(drop=True)
        predictor_refer[i].fit(train_x,train_y)    
        pred_set=predictor_refer[i].predict_proba(train_x)
        tensor_train[position,i+1,:]=torch.FloatTensor(pred_set)
        
        cluster=x_categorical_test[name]
        position=(cluster==true_levels[i])
        test_x=pd.DataFrame(enc_set.transform(x_categorical_test.iloc[:,feature_selection_categorical[i+1]]).toarray())[position].reset_index(drop=True)
        test_x=test_x.join(x_continuous_test.iloc[:,feature_selection_continous[i+1]].loc[position].reset_index(drop=True))
        test_y=target_test[position].reset_index(drop=True)
        pred_set=predictor_refer[i].predict_proba(test_x)
        tensor_test[position,i+1,:]=torch.FloatTensor(pred_set)
        
        pred=predictor_refer[i].predict(test_x)
        con=sklearn.metrics.confusion_matrix(target_test[position].reset_index(drop=True),pred,labels=label)
        precision=np.zeros(len(con)+1)
        t=0.0
        for j in range(len(con)):
            precision[j]=con[j,j]/sum(con[:,j])
            t+=con[j,j]
        precision[len(con)]=t/sum(sum(con))
        precision_refer[i,:]=copy.copy(precision) 
    ############################################################################## 
    
    ###############################################################################
    #network train:
    enc_target=preprocessing.LabelEncoder()
    enc_target.fit(target.append(target_test))
    target_train=enc_target.transform(target)
    target_train=torch.LongTensor(target_train)
    target_validation=enc_target.transform(target_test)
    target_validation=torch.LongTensor(target_validation)
    
    kernel=dicision_kernel()
    #
    temp=torch.Tensor(np.zeros([kernel.linear1.weight.size()[0],kernel.linear1.weight.size()[1]]))
    for i in range(kernel.linear1.weight.size()[0]):
        temp[i,i]=1
    kernel.linear1.weight=torch.nn.Parameter(temp)
    kernel.linear1.bias=torch.nn.Parameter(torch.Tensor(np.zeros(kernel.linear1.weight.size()[0])))
    #
    #epoch=1000
    criterion = nn.CrossEntropyLoss()
    optimizer_1 = optim.SGD(kernel.parameters(), lr=0.01)
    optimizer_2 = optim.SGD(kernel.parameters(), lr=0.001)
    trainloader = DataLoader(TensorDataset(tensor_train,target_train), batch_size=128,shuffle=True)
    
    precision_record=np.zeros([epoch])
    loss_record=np.zeros([epoch])
    
    for ite in range(epoch):
        if ite<10:
            optimizer=optimizer_1
        else:
            optimizer=optimizer_2
        Loss=0
        for i,temp in enumerate(trainloader,0):
            [train_x,train_y]=temp
            optimizer.zero_grad()
            outputs=kernel(train_x)
            loss=criterion(outputs,train_y)
            loss.backward()
            optimizer.step()
            Loss+=loss.detach().numpy()    
        Loss=Loss/(i+1)
        loss_record[ite]=Loss
        print(ite+1)
        print('loss: %.5f' % (Loss))
        with torch.no_grad():
            outputs_validation=kernel(tensor_test)
            position=list(outputs_validation.argmax(axis=1))
            pred=[]
            for j in range(len(position)):
                pred=pred+[label[position[j]]]
            precision=sum(pred==target_test)/len(target_test)
            print('precision: %.5f' % (precision))
            precision_record[ite]=precision

    Precision_0+=precision_0
    #Precision_refer+=precision_refer
    Precision_record+=precision_record
    Loss_record+=loss_record
    
Precision_0=Precision_0/10
#Precision_refer=Precision_refer/10
Precision_record=Precision_record/10   
Loss_record=Loss_record/10
    
    
plt.plot(range(len(Precision_record)),Precision_record,label="XGboost+CNN")   
plt.legend()
#plt.plot([0,999],[0.90725716,0.90725716],'--',label='base line')
plt.legend()        
plt.xlabel('Number of epochs')
plt.ylabel('testing accuracy')
    
    
plt.plot(range(len(Loss_record)),Loss_record)   
#plt.legend()
#plt.plot([0,999],[0.90725716,0.90725716],'--',label='Asymptote line')
#plt.legend()        
plt.xlabel('Number of epochs')
plt.ylabel('Training loss')    
    
    
