# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,'..')

import torch
torch.manual_seed(42)
import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from ceml.torch import generate_counterfactual
from ceml.backend.torch.costfunctions import NegLogLikelihoodCost
from ceml.model import ModelWithLoss


def test_softmaxregression():
    # Neural network - Softmax regression
    class Model(torch.nn.Module, ModelWithLoss):
        def __init__(self, input_size, num_classes):
            super(Model, self).__init__()

            self.linear = torch.nn.Linear(input_size, num_classes)
            self.softmax = torch.nn.Softmax(dim=0)
        
        def forward(self, x):
            return self.linear(x)   # NOTE: Softmax is build into CrossEntropyLoss
        
        def predict_proba(self, x):
            return self.softmax(self.forward(x))
        
        def predict(self, x, dim=1):
            return torch.argmax(self.forward(x), dim=dim)
        
        def get_loss(self, y_target, pred=None):
            return NegLogLikelihoodCost(self.predict_proba, y_target)

    # Load data
    X, y = load_iris(True)
    X = X.astype(np.dtype(np.float32))

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=1)

    # numpy -> torch tensor
    x = torch.from_numpy(X_train)
    labels = torch.from_numpy(y_train)

    x_test = torch.from_numpy(X_test)
    y_test = torch.from_numpy(y_test)

    # Create and fit model
    model = Model(4, 3)

    learning_rate = 0.001
    momentum = 0.9
    criterion = torch.nn.CrossEntropyLoss()

    optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate, momentum=momentum)  

    num_epochs = 800
    for epoch in range(num_epochs):
        optimizer.zero_grad()
        outputs = model(x)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

    # Evaluation
    y_pred = model.predict(x_test).numpy()
    assert accuracy_score(y_test, y_pred) >= 0.8

    # Select data point for explaining its prediction
    x_orig = X_test[1,:]
    assert model.predict(torch.from_numpy(np.array([x_orig]))).numpy() == 1

    # Compute counterfactual
    features_whitelist = None

    optimizer = "bfgs"
    optimizer_args = {"max_iter": 1000, "args": {"lr": 0.9, "momentum": 0.9}}
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization="l2", C=0.001, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0

    optimizer = "nelder-mead"
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization="l2", C=0.001, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0

    optimizer = torch.optim.SGD
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization="l2", C=0.001, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0

    optimizer = "bfgs"
    optimizer_args = {"max_iter": 1000, "args": {"lr": 0.9, "momentum": 0.9}}
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization=None, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0

    optimizer = torch.optim.SGD
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization=None, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0


    features_whitelist = [0, 2]

    optimizer = "bfgs"
    optimizer_args = {"max_iter": 1000, "args": {"lr": 0.9, "momentum": 0.9}}
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization="l2", C=0.001, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0
    assert all([True if i in features_whitelist else delta[i] == 0. for i in range(x_orig.shape[0])])

    optimizer = "nelder-mead"
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization="l2", C=0.001, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0
    assert all([True if i in features_whitelist else delta[i] == 0. for i in range(x_orig.shape[0])])

    optimizer = torch.optim.SGD
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization="l2", C=0.001, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0
    assert all([True if i in features_whitelist else delta[i] == 0. for i in range(x_orig.shape[0])])

    optimizer = "bfgs"
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization=None, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0
    assert all([True if i in features_whitelist else delta[i] == 0. for i in range(x_orig.shape[0])])

    optimizer = torch.optim.SGD
    x_cf, y_cf, delta = generate_counterfactual(model, x_orig, y_target=0, features_whitelist=features_whitelist, regularization=None, optimizer=optimizer, optimizer_args=optimizer_args, return_as_dict=False)
    assert y_cf == 0
    assert model.predict(torch.from_numpy(np.array([x_cf], dtype=np.float32))).numpy() == 0
    assert all([True if i in features_whitelist else delta[i] == 0. for i in range(x_orig.shape[0])])