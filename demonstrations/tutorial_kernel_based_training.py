"""
.. _kernel_based_training:

.. role:: html(raw)
   :format: html

Kernel-based training with scikit-learn
=======================================

.. meta:: 
    :property=“og:description”: Kernel-based training with scikit-learn. 
    :property=“og:image”: https://pennylane.ai/qml/_images/kernel_based_scaling.png

.. related::

    tutorial_variational_classifier Variational classifier
    
This demonstration illustrates how one can train quantum machine
learning models with a kernel-based approach instead of the usual
`variational
approach <https://pennylane.ai/qml/glossary/variational_circuit.html>`__.
The theoretical background has been established in many papers in the literature 
such as `Havlicek et al. (2018) <https://arxiv.org/abs/1804.11326>`__, `Schuld and Killoran (2018) <https://arxiv.org/abs/1803.07128>`__,
`Liu et al. (2020) <https://arxiv.org/abs/2010.02174>`__, `Huang et al. (2020) <https://arxiv.org/pdf/2011.01938.pdf>`__,
and has been systematically summarised in the overview `Schuld (2021) <https://arxiv.org/abs/2101.11020>`__ which we follow here.

As an example of kernel-based training we use a combination of PennyLane
and the powerful `scikit-learn <https://scikit-learn.org/>`__ machine
learning library to use a support vector machine with 
a "quantum kernel". We then compare this strategy with a variational
quantum circuit trained via stochastic gradient descent using
PyTorch.

A secondary goal of the demo is to estimate the number of circuit evaluations needed in
both approaches. We will see that while kernel-based training famously scales much worse than 
neural networks, the comparison with variational training depends on how many parameters the variational 
ansatz requires as the data size grows. If variational circuits turn out to be similar to neural nets and grow linearly in size 
with the data, kernel-based training is much more efficient. 
If instead the number of parameters plateaus with growing data sizes, variational training would require fewer circuit 
evaluations. 

.. figure::  ../demonstrations/kernel_based_training/scaling.png 
       :align: center
       :scale: 100%
       :alt: Scaling of kernel-based vs. variational learning
       
"""

######################################################################
# Background
# ==========
#
# Let us consider a "quantum model" of the form
#
# .. math:: f(x) = \langle \phi(x) | \mathcal{M} | \phi(x)\rangle,
#
# where :math:`| \phi(x)\rangle` is prepared
# by a fixed `embedding
# circuit <https://pennylane.readthedocs.io/en/stable/introduction/templates.html#intro-ref-temp-emb>`__ that 
# encodes data inputs :math:`x`,
# and :math:`\mathcal{M}` is an arbitrary observable. This model includes variational 
# quantum machine learning models, since the observable can
# effectively be implemented by a simple measurement that is preceded by a
# variational circuit. 
#
# .. figure:: ../demonstrations/kernel_based_training/quantum_model.png 
#       :align: center
#       :scale: 30%
#       :alt: quantum-model
#
# If the circuit is trainable, the measurement becomes
# trainable. For example, applying a circuit :math:`B(\theta)` and then
# measuring the PauliZ observable :math:`\sigma^0_z` of the first qubit
# implements the effective measurement observable
# :math:`\mathcal{M}(\theta) = B^{\dagger}(\theta) \sigma^0_z B(\theta)`.
#
# The main practical consequence of approaching quantum machine learning with a 
# kernel approach is that instead of training $f$ variationally,
# we can often train a classical kernel method with a kernel executed on a
# quantum device. This “quantum kernel"
# is given by the mutual overlap of two data-encoding quantum states,
#
# .. math::  \kappa(x, x') = | \langle \phi(x') | \phi(x)\rangle|^2.
#
# Kernel-based training therefore by-passes the variational part and
# measurement of common variational circuits, and only depends on the
# embedding.
#
# .. note::
#
#    More precisely, we can replace variational training with kernel-based training if the optimisation
#    problem can be written as minimising a cost of the form

#    .. math:: f_{\rm trained} = \min_f  \lambda \mathrm{tr}\{\mathcal{M^2\} + \frac{1}{M}\sum_{m=1}^M L(f(x^m), y^m),
 
#    which is a regularised empirical risk of training data samples:math:`(x^m, y^m)_{m=1\dots M}` and loss function :math:`L`.
#
# If the loss function in training is the `hinge
# loss <https://en.wikipedia.org/wiki/Hinge_loss>`__, the kernel method
# corresponds to a standard `support vector
# machine <https://en.wikipedia.org/wiki/Support-vector_machine>`__ (SVM)
# in the sense of a maximum-margin classifier. Other convex loss functions
# lead to more general variations of support vector machines.
#
# .. warning::
#
#    Theory predicts that kernel-based training will always find better or equally good
#    models :math:`f_{\rm trained}` for the optimisation problem stated above. However, to show this here we would have
#    to either regularise the variational training by a term :math:`\mathrm{tr}\{\mathcal{M^2\}`, or switch off
#    regularisation in the classical SVM, which denies the SVM a lot of its strength. The kernel-based and the variational 
#    training in this demonstration therefore optimize slightly different cost
#    functions, and it is out of our scope to establish whether one training method finds a better minimum than
#    the other.
#


######################################################################
# Kernel-based training
# =====================
#


######################################################################
# First, let’s import all sorts of useful methods:
#

import numpy as np
import torch
from torch.nn.functional import relu

from sklearn.svm import SVC
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

import pennylane as qml
from pennylane.templates import AngleEmbedding, StronglyEntanglingLayers
from pennylane.operation import Tensor

import matplotlib.pyplot as plt

np.random.seed(42)


######################################################################
# The second step is to make an artificial toy data set.
#

X, y = make_blobs(n_samples=150, n_features=3, centers=2, cluster_std=1.5)

# scaling the inputs is important since the embedding we use is periodic
scaler = StandardScaler().fit(X)
X_scaled = scaler.transform(X)

# scaling the labels to -1, 1 is important for the SVM and the
# definition of a hinge loss
y_scaled = 2 * (y - 0.5)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_scaled)


######################################################################
# We will use the `amplitude embedding
# template <https://pennylane.readthedocs.io/en/stable/code/api/pennylane.templates.embeddings.AmplitudeEmbedding.html>`__
# which needs as many qubits as there are features.
#

n_qubits = len(X_train[0])


######################################################################
# To implement the kernel we could prepare the two states
# :math:`| \phi(x)\rangle`, :math:`| \phi(x')\rangle` on different qubits
# with amplitude embedding routines :math:`S(x), S(x')` and measure their
# overlap with a small routine called a SWAP test.
#
# However, we need only half the number of qubits if we prepare
# :math:`| \phi(x)\rangle` and then apply the inverse embedding
# with :math:`x'` on the same qubits. We then measure the projector onto
# the initial state :math:`|0\rangle \langle 0|`.
#
# .. figure:: ../demonstrations/kernel_based_training/kernel_circuit.png 
#       :align: center
#       :scale: 100% 
#       :alt: Kernel evaluation circuit
#
# To verify that this gives us the kernel:
#
# .. math::  \langle 0 |S(x') S(x)^{\dagger} |0\rangle \langle 0| S(x')^{\dagger} S(x)  | 0\rangle  = | \langle \phi(x') | \phi(x)\rangle|^2 = \kappa(x, x').
#
# Note that a projector :math:`|0 \rangle \langle 0|` can be constructed
# as follows in PennyLane:
#
# .. code:: python
#
#    observables = [qml.PauliZ(i) for i in range(n_qubits)]
#    projector = Tensor(*observables)
#
# Altogether, we use the following quantum node as a “quantum kernel
# evaluator”:
#

dev_kernel = qml.device("default.qubit", wires=n_qubits)

observables = [qml.PauliZ(i) for i in range(n_qubits)]

@qml.qnode(dev_kernel)
def kernel(x1, x2):
    """
    The quantum kernel.
    """
    AngleEmbedding(x1, wires=range(n_qubits))
    qml.inv(AngleEmbedding(x2, wires=range(n_qubits)))
    return qml.expval(Tensor(*observables))


######################################################################
# A good sanity check is whether measuring the distance between one and
# the same data point returns 1:
#

kernel(X_train[0], X_train[0])


######################################################################
# The way an SVM with a custom kernel is implemented in scikit-learn
# requires us to pass a function that computes a matrix of kernel
# evaluations for samples in two different datasets A, B.
#


def kernel_matrix(A, B):
    """
    Compute the matrix whose entries are the kernel
    evaluated on pairwise data from sets A and B.
    If A=B, this is the Gram matrix.
    """
    return np.array([[kernel(a, b) for b in B] for a in A])


######################################################################
# Training the SVM is a breeze in scikit-learn:
#

svm = SVC(kernel=kernel_matrix).fit(X_train, y_train)


######################################################################
# Let’s compute the accuracy on the test set.
#

predictions = svm.predict(X_test)
accuracy_score(predictions, y_test)


######################################################################
# How many times was the quantum device evaluated?
#

dev_kernel.num_executions


######################################################################
# This number can be derived as follows: For :math:`M` training samples,
# the SVM must construct the :math:`M \times M` dimensional kernel gram
# matrix for training. To classify :math:`M_{\rm pred}` new samples, the
# SVM needs to evaluate the kernel at most :math:`M_{\rm pred}M` times to get the
# pairwise distances between training vectors and test samples.
#
# .. note:: 
#    
#     Depending on the implementation of the SVM, only :math:`S \leq M_{\rm pred}`
#     *support vectors* are needed. 
#
# Overall, the number of kernel evaluations of the above script should
# therefore roughly amount to at most:
#


def circuit_evals_kernel(n_data, split):
    """
    Compute how many circuit evaluations one needs for kernel-based training and prediction.
    """

    M = int(np.ceil(0.75 * n_data))
    Mpred = n_data - M

    n_training = M * M
    n_prediction = M * Mpred

    return n_training + n_prediction


circuit_evals_kernel(n_data=len(X), split=len(X_train) / len(X_test))


######################################################################
# A similar example using variational training
# ============================================
#


######################################################################
# Using the variational principle of training, we can propose an *ansatz*
# for the (circuit before the) measurement and train it directly. By
# increasing the number of layers of the ansatz, its expressivity
# increases. Depending on the ansatz, we can express any measurement, or
# only search through a subspace of all measurements for the best
# candidate.
#
# Remember from above, the variational training does not optimise
# *exactly* the same cost as the SVM, but we try to match them as closely
# as possible. For this we use a bias term in the quantum model, and train
# on the hinge loss.
#

dev_var = qml.device("default.qubit", wires=n_qubits)


@qml.qnode(dev_var, interface="torch", diff_method="parameter-shift")
def quantum_model(x, params):
    """
    A variational circuit approximation of the quantum model.
    """
    # embedding
    AngleEmbedding(x, wires=range(n_qubits))

    # trainable measurement
    StronglyEntanglingLayers(params, wires=range(n_qubits))
    return qml.expval(qml.PauliZ(0))


def quantum_model_plus_bias(x, params, bias):
    """
    Adding a bias.
    """
    return quantum_model(x, params) + bias


def hinge_loss(predictions, targets):
    """
    Implements the hinge loss.
    """
    all_ones = torch.ones_like(targets)
    hinge_loss = all_ones - predictions * targets
    # trick: since the max function is not diffable,
    # use the mathematically equivalent relu instead
    hinge_loss = relu(hinge_loss)
    return hinge_loss


######################################################################
# We now summarise the usual training and prediction steps into two
# functions that we can later call at will. Most of the work is to
# convert between numpy and torch, which we need for the differentiable
# ``relu`` function used in the hinge loss.
#


def quantum_model_train(n_layers, steps, batch_size):
    """
    Train the quantum model defined above.
    """
    params = np.random.random((2, n_qubits, 3))
    params_torch = torch.tensor(params, requires_grad=True)
    bias_torch = torch.tensor(0.0)

    opt = torch.optim.Adam([params_torch, bias_torch], lr=0.1)

    loss_history = []
    for i in range(steps):

        batch_ids = np.random.choice(len(X_train), batch_size)

        X_batch = X_train[batch_ids]
        y_batch = y_train[batch_ids]

        X_batch_torch = torch.tensor(X_batch, requires_grad=False)
        y_batch_torch = torch.tensor(y_batch, requires_grad=False)

        def closure():
            opt.zero_grad()
            preds = torch.stack(
                [quantum_model_plus_bias(x, params_torch, bias_torch) for x in X_batch_torch]
            )
            loss = torch.mean(hinge_loss(preds, y_batch_torch))

            # bookkeeping
            current_loss = loss.detach().numpy().item()
            loss_history.append(current_loss)
            if i % 10 == 0:
                print("step", i, ", loss", current_loss)

            loss.backward()
            return loss

        opt.step(closure)

    return params_torch, bias_torch, loss_history


def quantum_model_predict(X_pred, trained_params, trained_bias):
    """
    Predict using the quantum model defined above.
    """
    p = []
    for x in X_pred:

        x_torch = torch.tensor(x)
        pred_torch = quantum_model_plus_bias(x_torch, trained_params, trained_bias)
        pred = pred_torch.detach().numpy().item()
        if pred > 0:
            pred = 1
        else:
            pred = -1

        p.append(pred)
    return p


######################################################################
# Let’s train the variational model and see how well we are doing on the
# test set.
#

n_layers = 1
batch_size = 20
steps = 80
trained_params, trained_bias, loss_history = quantum_model_train(n_layers, steps, batch_size)

pred_test = quantum_model_predict(X_test, trained_params, trained_bias)
print("accuracy on test set:", accuracy_score(pred_test, y_test))

plt.plot(loss_history)
plt.ylim((0, 1))
plt.show()


######################################################################
# How often was the device executed?
#

dev_var.num_executions


######################################################################
# Let’s do another calculation: In each optimisation step, the variational
# circuit needs to compute the partial derivative of all :math:`K`
# trainable parameters for each sample in a batch. Using `parameter-shift
# rules <https://pennylane.ai/qml/glossary/parameter_shift.html>`__ we require roughly 2 circuit
# evaluations per partial derivative. Prediction uses only one circuit
# evaluation per sample.
#
# We roughly get:
#


def circuit_evals_variational(n_data, n_params, n_steps, evals_per_derivative, split,  batch_size):
    """
    Compute how many circuit evaluations are needed for variational training and prediction.
    """

    M = int(np.ceil(0.75 * n_data))
    Mpred = n_data - M

    n_training = n_params * n_steps * batch_size * evals_per_derivative
    n_prediction = Mpred

    return n_training + n_prediction


circuit_evals_variational(
    n_data=len(X),
    n_params=len(trained_params.flatten()),
    n_steps=steps,
    evals_per_derivative=2,
    split=len(X_train) / len(X_test),
    batch_size=batch_size,
)


######################################################################
# It is important to note that while they are trained in a similar manner, 
# the number of variational circuit evaluations differs from the number of 
# neural network model evaluations in classical machine learning, which would be given by:
#

def model_evals_nn(n_data, n_params, n_steps, split,  batch_size):
    """
    Compute how many model evaluations are needed for neural network training and prediction.
    """

    M = int(np.ceil(0.75 * n_data))
    Mpred = n_data - M

    n_training = n_steps * batch_size
    n_prediction = Mpred

    return n_training + n_prediction
    
######################################################################
# In each step of neural network training, due to the power of automatic differentiation 
# the backpropagation algorithm can compute a 
# gradient for all parameters in (more-or-less) a single run. 
# For all we know at this stage, the no-cloning principle prevents variational circuits to use these tricks, 
# which leads to ``n_training`` in ``circuit_evals_variational`` depend on the number of parameters, but not in 
# ``model_evals_nn``. 
#
# For the same example as used here, a neural network would therefore 
# have much fewer model evaluations:
#

model_evals_nn(
    n_data=len(X),
    n_params=len(trained_params.flatten()),
    n_steps=steps,
    split=len(X_train) / len(X_test),
    batch_size=batch_size,
)
   

######################################################################
# Which method scales best?
# =========================
#


######################################################################
# In the example above, kernel-based training trumps variational
# training in the number of circuit evaluations. But how does the overall scaling
# look like? 
#
# Of course, the answer to this question depends on how the variational model 
# is set up, and we need to make a few assumptions: 
#
# 1. Even if we use single-batch stochastic gradient descent, in which every training step uses 
#    exactly one training sample, we would want to see every training sample at least once on average. 
#    Therefore, the number of steps should scale linearly with the number of training data. 
#
# 2. Modern neural networks often have many more parameters than training
#    samples. But we do not know yet whether variational circuits really need that many parameters as well.
#    We will therefore use two cases for comparison: 
#
#    a) the number of parameters grows linearly with the training data, or ``n_params = M``, 
#
#    b) the number of parameters grows as the square root with the training data, or ``n_params = np.sqrt(M)``. 
#
# Note that compared to the example above with 112 training samples and 18 parameters, a) overestimates the number of evaluations, while b) 
# underestimates it.
#


######################################################################
# This is how the three methods compare:
#

variational_training1 = []
variational_training2 = []
kernelbased_training = []
nn_training = []
x_axis = range(0, 2000, 100)
for M in x_axis:

    var1 = circuit_evals_variational(
        n_data=M, n_params=M, n_steps=M,  evals_per_derivative=2, split=0.75, batch_size=1
    )
    variational_training1.append(var1)

    var2 = circuit_evals_variational(
        n_data=M, n_params=round(np.sqrt(M)), n_steps=M,  evals_per_derivative=2, split=0.75, batch_size=1
    )
    variational_training2.append(var2)
    
    kernel = circuit_evals_kernel(n_data=M, split=0.75)
    kernelbased_training.append(kernel)
    
    nn = model_evals_nn(
        n_data=M, n_params=M, n_steps=M, split=0.75, batch_size=1
    )
    nn_training.append(nn)


plt.plot(x_axis, nn_training, linestyle='--', label="neural net")
plt.plot(x_axis, variational_training1, label="var. circuit (linear param scaling)")
plt.plot(x_axis, variational_training2, label="var. circuit (srqt param scaling)")
plt.plot(x_axis, kernelbased_training, label="(quantum) kernel")
plt.xlabel("size of data set")
plt.ylabel("number of evaluations")
plt.legend()
plt.tight_layout()
plt.show()



######################################################################
# Under the assumptions made, the relation between kernel-based 
# and variational quantum machine learning depends on how many parameters the latter need: 
# If variational circuits turn out to be as parameter-hungry as neural networks,
# kernel-based training will consistently outperform it. 
# However, if we find ways to train variational circuits with few parameters,
# they can catch up with the good scaling neural networks draw from backpropagation.   
#
# However, fault-tolerant quantum computers may change the picture significantly. 
# As mentioned in `Schuld (2021) <https://arxiv.org/abs/2101.11020>`__, 
# early results from the quantum machine learning literature show that
# larger quantum computers enable us in principle to reduce
# the quadratic scaling of kernel methods to linear scaling, which may make kernel methods a
# serious alternative to neural networks (and of course variational circuits) for big data processing one day.
#