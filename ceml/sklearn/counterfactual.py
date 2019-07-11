# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from ..optim import InputWrapper, desc_to_optim
from ..model import Counterfactual
from ..backend.jax.costfunctions import RegularizedCost
from .utils import build_regularization_loss, wrap_input


class SklearnCounterfactual(Counterfactual, ABC):
    """Base class for computing a counterfactual of a `sklearn` model.

    The :class:`SklearnCounterfactual` class can compute counterfactuals of `sklearn` models.

    Parameters
    ----------
    model : object
        The `sklearn` model that is used for computing the counterfactual.

    Attributes
    ----------
    model : object
        An instance of a `sklearn` model.
    mymodel : instance of :class:`ceml.model.ModelWithLoss`
        Rebuild model.

    Note
    ----
    The class :class:`SklearnCounterfactual` can not be instantiated because it contains an abstract method. 
    """
    def __init__(self, model):
        self.model = model
        self.mymodel = self.rebuild_model(model)

        super(SklearnCounterfactual, self).__init__()

    @abstractmethod
    def rebuild_model(self, model):
        """Rebuilds a `sklearn` model.

        Converts a `sklearn` model into a class:`ceml.model.ModelWithLoss` instance so that we have a model specific cost function and can compute the derivative with respect to the input.

        Parameters
        ----------
        model
            The `sklearn` model that is used for computing the counterfactual.
        
        Returns
        -------
        :class:`ceml.model.ModelWithLoss`
            The wrapped `model`
        """
        raise NotImplementedError()

    def wrap_input(self, features_whitelist, x, optimizer):
        return wrap_input(features_whitelist, x, self.mymodel, optimizer)
    
    """
    Build a loss function and compute its gradient.

    Note
    ----
    If the loss is not differentiable, you have to overwrite this function!
    """
    def build_loss(self, regularization, x_orig, y_target, pred, grad_mask, C, input_wrapper):
        regularization = build_regularization_loss(regularization, x_orig)

        loss = RegularizedCost(regularization, self.mymodel.get_loss(y_target, pred), C=C)
        loss_grad = loss.grad(grad_mask)

        return loss, loss_grad

    def __build_result_dict(self, x_cf, y_cf, delta):
        return {'x_cf': x_cf, 'y_cf': y_cf, 'delta': delta}

    def compute_counterfactual_ex(self, x, loss, x0, loss_grad, optimizer, input_wrapper, return_as_dict):
        solver = desc_to_optim(optimizer, loss, x0, loss_grad)

        x_cf = input_wrapper(solver())
        y_cf = self.model.predict([x_cf])[0]
        delta = x - x_cf

        if return_as_dict is True:
            return self.__build_result_dict(x_cf, y_cf, delta)
        else:
            return x_cf, y_cf, delta

    def compute_counterfactual(self, x, y_target, features_whitelist=None, regularization="l1", C=1.0, optimizer="nelder-mead", return_as_dict=True, done=None):
        """Computes a counterfactual of a given input `x`.

        Parameters
        ----------
        x : `numpy.ndarray`
            The input `x` whose prediction has to be explained.
        y_target : `int` or `float`
            The desired prediction of the counterfactual.
        feature_whitelist : `list(int)`, optional
            List of feature indices (dimensions of the input space) that can be used when computing the counterfactual.
            
            If `feature_whitelist` is None, all features can be used.

            The default is None.
        regularization : `str` or :class:`ceml.costfunctions.costfunctions.CostFunction`, optional
            Regularizer of the counterfactual. Penalty for deviating from the original input `x`.
            Supported values:
            
                - l1: Penalizes the absolute deviation.
                - l2: Penalizes the squared deviation.

            `regularization` can be a description of the regularization, an instance of :class:`ceml.costfunctions.costfunctions.CostFunction` (or :class:`ceml.costfunctions.costfunctions.DifferentiableCostFunction` if the cost function is differentiable) or None if no regularization is requested.

            If `regularization` is None, no regularization is used.

            The default is "l1".
        C : `float` or `list(float)`, optional
            The regularization strength. If `C` is a list, all values in `C` are tried and as soon as a counterfactual is found, this counterfactual is returned and no other values of `C` are tried.

            If no regularization is used (`regularization=None`), `C` is ignored.

            The default is 1.0
        optimizer : `str`, optional
            Name/Identifier of the optimizer that is used for computing the counterfactual.

            See :func:`ceml.optimizer.optimizer.desc_to_optim` for details.

            The default is "nelder-mead".
        return_as_dict : `boolean`, optional
            If True, returns the counterfactual, its prediction and the needed changes to the input as dictionary.
            If False, the results are returned as a triple.

            The default is True.
        done : `callable`, optional
            A callable that returns `True` if a counterfactual with a given output/prediction is accepted and `False` otherwise.

            If `done` is None, the output/prediction of the counterfactual must match `y_target` exactly.

            The default is None.

            Note
            ----
            In case of a regression it might not always be possible to achieve a given output/prediction exactly.

        Returns
        -------
        `dict` or `triple`
            A dictionary where the counterfactual is stored in 'x_cf', its prediction in 'y_cf' and the changes to the original input in 'delta'.

            (x_cf, y_cf, delta) : triple if `return_as_dict` is False
        
        Raises
        ------
        Exception
            If no counterfactual was found.
        """
        # Hide the input in a wrapper if we can use a subset of features only
        input_wrapper, x_orig, pred, grad_mask = self.wrap_input(features_whitelist, x, optimizer)
        
        # Repeat for all C
        if not type(C) == list:
            C = [C]
        done = done if done is not None else y_target if callable(y_target) else lambda y: y == y_target
        
        for c in C:
            # Build loss
            loss, loss_grad = self.build_loss(regularization, x_orig, y_target, pred, grad_mask, c, input_wrapper)

            # Compute counterfactual
            x_cf, y_cf, delta = self.compute_counterfactual_ex(x, loss, x_orig, loss_grad, optimizer, input_wrapper, False)

            if done(y_cf) == True:
                if return_as_dict is True:
                    return self.__build_result_dict(x_cf, y_cf, delta)
                else:
                    return x_cf, y_cf, delta
        
        raise Exception("No counterfactual found - Consider changing parameters 'C', 'regularization', 'features_whitelist', 'optimizer' and try again")
    
    def __call__(self, x, y_target, features_whitelist=None, regularization="l1", C=1.0, optimizer="nelder-mead", return_as_dict=True):
        return self.compute_counterfactual(x, y_target, features_whitelist, regularization, C, optimizer, return_as_dict)