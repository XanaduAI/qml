r"""
.. role:: html(raw)
   :format: html

Photonic quantum advantage with Gaussian Boson Sampling
=======================================================

.. meta::
    :property="og:description": Using states of light carry out tasks beyond the reach of classical computers.
    :property="og:image": https://pennylane.ai/qml/_images/qonn_thumbnail.png

.. related::

    tutorial_gaussian_transformation Gaussian transformation
    qsim_beyond_classical Beyond classical computing with qsim
    qonn Optimizing a quantum optical neural network
    
On the journey to large-scale fault-tolerant quantum computers, one of the first major 
milestones is to demonstrate a quantum device carrying out tasks which are beyond the reach of 
any classical algorithm. The Google Quantum team was the first to claim this achievement, 
announced in their paper `Quantum supremacy using a programmable superconducting
processor <https://www.nature.com/articles/s41586-019-1666-5>`__ [[#Arute2019]_]. Now a team led 
by Chao-Yang Lu and Jian-Wei Pan has performed a similar feat using quantum photonics. While 
Google's experiment performed the task of :ref:`random circuit sampling <qsim_beyond_classical>` 
using a superconducting processor, the new experiment, published in the paper 
`Quantum computational advantage using photons 
<https://science.sciencemag.org/content/early/2020/12/02/science.abe8770?rss=1>`__ 
[[#Zhong2020]_] leverages the quantum properties of light to tackle a task called 
`Gaussian Boson Sampling <https://strawberryfields.ai/photonics/concepts/gbs.html>`__ (GBS).

This tutorial will walk you through the basic elements of GBS, motivate why simulating it is
classically challenging, and show how you can explore GBS using PennyLane and the photonic 
quantum devices accessible via the 
`PennyLane-Strawberry Fields plugin <https://pennylane-sf.readthedocs.io>`__.

The origin of GBS
-----------------

Let's first explain the name. `boson <https://en.wikipedia.org/wiki/Boson>` refers to bosonic 
matter, which, along with fermions, makes up one of the two elementary classes of particles. 
The most prevalent bosonic system in our everyday lives is light, which is made of particles 
called photons. Another famous example, though much harder to find, is the Higgs boson. 
The distinguishing characteristic of bosons is that they follow "Bose-Einstein statistics", 
which very loosely means that the particles like to bunch together (contrast this to fermionic 
matter like electrons, which must follow the Pauli Exclusion Principle and keep apart). 

This property can be observed in simple interference experiments such as the 
`Hong-Ou Mandel setup <https://en.wikipedia.org/wiki/Hong%E2%80%93Ou%E2%80%93Mandel_effect>`__.
If two single photons are interfered on a balanced beamsplitter, they will both emerge at 
the same output port---there is zero probability that they will emerge at separate outputs. 
This is a simple but notable quantum property of light; if electrons were brought 
together in a similar experiement, they would always appear at separate output ports.

Gaussian Boson Sampling is, in fact, a member of a larger family of "Boson Sampling" algorithms, 
stemming back to the initial proposal of Aaronson and Arkhipov [#aaronson2013]_ in 2013. 
Boson Sampling is quantum interferometry writ large. Aaronson and Arkhipov's original proposal 
was to inject many single photons into distinct input ports of a large interferometer, then 
measure which output ports they appear at. The natural interference properties of bosons
means that photons will appear at the output ports in very unique and specific ways. Boson 
Sampling was not proposed with any kind of practical real-world use-case in mind. Like
the random circuit sampling, it's just a quantum system being its best self. With sufficient
size and quality, it is strongly believed to be hard for a classical computer to simulate this efficiently. 

Finally, the "Gaussian" in GBS refers to the fact that we vary the initial Boson Sampling 
proposal slightly: instead of injecting single photons---which are hard to jointly create in the 
size and quality needed to demonstrate Boson Sampling conclusively---we instead use states of 
light that is experimentally less demanding. These states of light are called "Gaussian" states, 
because they bear strong connections to the 
`Gaussian (or Normal) distribution <https://en.wikipedia.org/wiki/Normal_distribution>`__ 
from statistics. In [[#Zhong2020]_], they use a particular Gaussian state called a 
`squeezed state <https://en.wikipedia.org/wiki/Squeezed_states_of_light>`__.




, boson sampling presented a slight
deviation from the general approach in quantum computation. Rather than presenting a theoretical
model of universal quantum computation (i.e., a framework that enables quantum simulation of any
arbitrary Hamiltonian [#nielsen2010]_), boson sampling-based devices are instead an example
of an **intermediate quantum computer**, designed to experimentally implement a computation that
is thought to be intractable classically [#tillmann2013]_.

Boson sampling proposes the following `quantum linear optics
<https://en.wikipedia.org/wiki/Linear_optical_quantum_computing>`_ scheme. An array of single-photon
sources is set up, designed to simultaneously emit single photon states into a multimode linear
`interferometer <https://en.wikipedia.org/wiki/Interferometry>`_; the results are then generated by
sampling from the probability of single photon measurements from the output of the linear
interferometer.

While boson sampling allows the experimental implementation of a sampling problem that is countably
hard classically, one of the main issues it has in experimental setups is one of **scalability**,
due to its dependence on an array of simultaneously emitting single photon sources. Currently, most
physical implementations of boson sampling make use of a process known as `spontaneous parametric
down-conversion <http://en.wikipedia.org/wiki/Spontaneous_parametric_down-conversion>`_ to generate
the single-photon source inputs. However, this method is non-deterministic --- as the number of
modes in the apparatus increases, the average time required until every photon source emits a
simultaneous photon increases exponentially.

In order to simulate a deterministic single-photon source array, several variations on boson
sampling have been proposed; the most well-known being scattershot boson sampling [#lund2014]_.
However, a recent boson sampling variation by Hamilton et al. [#hamilton2017]_ mitigates the
need for single photon Fock states altogether, by showing that incident Gaussian states
--- in this case, single mode squeezed states --- can produce problems in the same computational
complexity class as boson sampling. Even more significantly, this negates the scalability
problem with single photon sources, as single mode squeezed states can be deterministically
generated simultaneously.

The Gaussian boson sampling scheme remains, on initial observation, quite similar to that of boson
sampling:

* :math:`N` single mode squeezed states :math:`\ket{z}`, with squeezing parameter
  :math:`z=re^{i\phi}`, enter an :math:`N` mode linear interferometer described by unitary :math:`U`
  simultaneously.

* Each output mode of the interferometer (denoted by state :math:`\ket{\psi'}`) is then measured in
  the Fock basis, :math:`\bigotimes_i n_i\ket{n_i}\bra{n_i}`.

Without loss of generality, we can absorb the squeezing phase parameter :math:`\phi` into the
interferometer, and set :math:`\phi=0` for convenience.

Using phase space methods, Hamilton et al. [#hamilton2017]_ showed that the probability of
measuring a Fock state containing only 0 or 1 photons per mode is given by

.. math::

    \left|\left\langle{n_1,n_2,\dots,n_N}\middle|{\psi'}\right\rangle\right|^2 =
    \frac{\left|\text{Haf}[(U(\bigoplus_i\tanh(r_i))U^T)]_{st}\right|^2}{\prod_{i=1}^N \cosh(r_i)}

i.e., the sampled single photon probability distribution is proportional to the **hafnian** of a
submatrix of :math:`U(\bigoplus_i\tanh(r_i))U^T`, dependent upon the output covariance matrix.

.. note::

    The hafnian of a matrix is defined by

    .. math:: \text{Haf}(A) = \frac{1}{n!2^n}\sum_{\sigma=S_{2N}}\prod_{i=1}^N A_{\sigma(2i-1)\sigma(2i)}

    where :math:`S_{2N}` is the set of all permutations of :math:`2N` elements. In graph theory, the
    hafnian calculates the number of perfect `matchings
    <https://en.wikipedia.org/wiki/Matching_(graph_theory)>`_ in an **arbitrary graph** with
    adjacency matrix :math:`A`.

    Compare this to the permanent, which calculates the number of perfect matchings on a *bipartite*
    graph - the hafnian turns out to be a generalization of the permanent, with the relationship

    .. math::

        \text{Per(A)} = \text{Haf}\left(\left[\begin{matrix}
            0&A\\ A^T&0
        \end{matrix}\right]\right)

As any algorithm that could calculate (or even approximate) the hafnian could also calculate the
permanent - a #P-hard problem - it follows that calculating or approximating the hafnian must also
be a classically hard problem.

Circuit construction and simulation
-----------------------------------

In quantum linear optics, the multimode linear interferometer is commonly decomposed into two-mode
beamsplitters (:class:`~pennylane.Beamsplitter`) and single-mode phase shifters
(:class:`~pennylane.PhaseShift`)
[#reck1994]_, allowing for a straightforward translation into a CV quantum circuit.

.. image:: /demonstrations/tutorial_gbs_circuit.svg
    :align: center
    :width: 70%
    :target: javascript:void(0);

.. raw:: html

    <br>

In the above, the single mode squeeze states all apply identical squeezing :math:`z=r`, the
parameters of the beamsplitters and the rotation gates determine the unitary :math:`U`, and finally
the detectors perform Fock state measurements on the output modes. As with boson sampling, for
:math:`N` input modes, we must have a minimum of :math:`N+1` columns in the beamsplitter array
[#clements2016]_.

Simulating this circuit using PennyLane is easy; we can simply read off the gates from left
to right, and convert it into a QNode.
"""

import numpy as np

# set the random seed
np.random.seed(42)

# import PennyLane
import pennylane as qml

######################################################################
# First, we must define the unitary matrix we would like to embed in the circuit.
# We will use SciPy to generate a Haar-random unitary:

from scipy.stats import unitary_group

# define the linear interferometer
U = unitary_group.rvs(4)
print(U)

######################################################################
# We can use this to now construct the circuit. First, we must create our device. Due to the lack
# of Fock states in the circuit, we use the Strawberry Fields Gaussian backend. The Gaussian
# backend is perfectly suited for simulation of Gaussian boson sampling, as all initial states
# are Gaussian, and all the required operators transform Gaussian states to other Gaussian
# states.

n_wires = 4
cutoff = 10

dev = qml.device("strawberryfields.gaussian", wires=n_wires, cutoff_dim=cutoff)

@qml.qnode(dev)
def gbs_circuit():
    # prepare the input squeezed states
    for i in range(n_wires):
        qml.Squeezing(1.0, 0.0, wires=i)

    # linear interferometer
    qml.Interferometer(U, wires=range(n_wires))
    return qml.probs(wires=range(n_wires))


######################################################################
# A couple of things to note in this particular example:
#
# 1. To prepare the input single mode squeezed vacuum state :math:`\ket{z}` where :math:`z = 1`, we
#    apply a squeezing gate :class:`~pennylane.Squeezing` to each of the wires (initially in
#    the vacuum state).
#
# 2. Next we apply the linear interferometer to all four wires, using
#    :class:`~pennylane.Interferometer`, and the unitary matrix ``U``. This operator
#    decomposes the unitary matrix representing the linear interferometer into single mode
#    rotation gates :class:`~pennylane.PhaseShift`, and two-mode beamsplitters
#    :class:`~pennylane.Beamsplitter`. After applying the interferometer, we will denote the
#    output state by :math:`\ket{\psi'}`.
#
# 3. Since Gaussian Boson Sampling is simulated in an infinite-dimensional Hilbert space,
#    we need to set an upper-limit on the maximum number of photons we can detect. This is the
#    ``cutoff`` value we defined above---we will only be considering detection events
#    with 9 photons or less per mode.
#
# Executing the QNode, and extracting the probability distribution:

probs = gbs_circuit().reshape([cutoff] * n_wires)
print(probs.shape)

######################################################################
# We now want to example the output probability data. For
# example, ``[1,2,0,1]`` represents the measurement resulting in the detection of 1 photon on wire
# ``0`` and wire ``3``, and 2 photons at wire ``1``, and would return the value
#
# .. math:: \text{prob}(1,2,0,1) = \left|\braketD{1,2,0,1}{\psi'}\right|^2
#
# Lets extract and view the probabilities of measuring various Fock states.

# Fock states to measure at output
measure_states = [(0,0,0,0), (1,1,0,0), (0,1,0,1), (1,1,1,1), (2,0,0,0)]

# extract the probabilities of calculating several
# different Fock states at the output, and print them out
for i in measure_states:
    print(f"|{''.join(str(j) for j in i)}>: {probs[i]}")

######################################################################
# Equally squeezed inputs
# -----------------------
#
# As shown earlier, the formula for calculating the output
# Fock state probability in Gaussian boson sampling is given by
#
# .. math::
#
#     \left|\left\langle{n_1,n_2,\dots,n_N}\middle|{\psi'}\right\rangle\right|^2 =
#     \frac{\left|\text{Haf}[(U\bigoplus_i\tanh(r_i)U^T)]_{st}\right|^2}{n_1!n_2!\cdots n_N!
#     \cosh(r_i)}
#
# where :math:`U` is the rotation/beamsplitter unitary transformation on the input and output mode
# annihilation and creation operators.
#
# However, in this particular example, we are using **the same** squeezing parameter, :math:`z=r`, for
# all input states - this allows us to simplify this equation. To start with, the hafnian expression
# simply becomes :math:`\text{Haf}[(UU^T\tanh(r))]_{st}`, removing the need for the tensor sum.
#
# Thus, we have
#
# .. math::
#
#     \left|\left\langle{n_1,n_2,\dots,n_N}\middle|{\psi'}\right\rangle\right|^2 =
#     \frac{\left|\text{Haf}[(UU^T\tanh(r))]_{st}\right|^2}{n_1!n_2!\cdots n_N!\cosh^N(r)}.
#
# Now that we have the interferometer unitary transformation :math:`U`, as well as the 'experimental'
# results, let's compare the two, and see if the Gaussian boson sampling result in the case of equally
# squeezed input modes, agrees with the PennyLane simulation probabilities.
#
# Calculating the hafnian
# ------------------------
#
# Before we can calculate the right hand side of the Gaussian boson sampling equation, we need a
# method of calculating the hafnian. Since the hafnian is classically hard to compute, it is not
# provided in either NumPy *or* SciPy, so we will use `The Walrus
# <https://the-walrus.readthedocs.io>`_ library, installed alongside Strawberry Fields:

from thewalrus import hafnian as haf

######################################################################
# Now, for the right hand side numerator, we first calculate the submatrix
# :math:`[(UU^T\tanh(r))]_{st}`:

B = (np.dot(U, U.T) * np.tanh(1))

######################################################################
# Unlike the boson sampling case, in Gaussian boson sampling, we determine the submatrix by taking the
# rows and columns corresponding to the measured Fock state. For example, to calculate the submatrix
# in the case of the output measurement :math:`\left|{1,1,0,0}\right\rangle`,

print(B[:, [0, 1]][[0, 1]])

######################################################################
# Comparing to the simulation
# ----------------------------
#
# Now that we have a method for calculating the hafnian, let's compare the output to that provided by
# the PennyLane QNode.
#
# **Measuring** :math:`\ket{0,0,0,0}` **at the output**
#
# This corresponds to the hafnian of an *empty* matrix, which is simply 1:

print(1 / np.cosh(1) ** 4)
print(probs[0, 0, 0, 0])

######################################################################
# **Measuring** :math:`\ket{1,1,0,0}` **at the output**

B = (np.dot(U, U.T) * np.tanh(1))[:, [0, 1]][[0, 1]]
print(np.abs(haf(B)) ** 2 / np.cosh(1) ** 4)
print(probs[1, 1, 0, 0])

######################################################################
# **Measuring** :math:`\ket{0,1,0,1}` **at the output**

B = (np.dot(U, U.T) * np.tanh(1))[:, [1, 3]][[1, 3]]
print(np.abs(haf(B)) ** 2 / np.cosh(1) ** 4)
print(probs[0, 1, 0, 1])

######################################################################
# **Measuring** :math:`\ket{1,1,1,1}` **at the output**
#
# This corresponds to the hafnian of the full matrix :math:`B=UU^T\tanh(r)`:

B = (np.dot(U, U.T) * np.tanh(1))
print(np.abs(haf(B)) ** 2 / np.cosh(1) ** 4)
print(probs[1, 1, 1, 1])

######################################################################
# **Measuring** :math:`\ket{2,0,0,0}` **at the output**
#
# Since we have two photons in mode ``q[0]``, we take two copies of the
# first row and first column, making sure to divide by :math:`2!`:

B = (np.dot(U, U.T) * np.tanh(1))[:, [0, 0]][[0, 0]]
print(np.abs(haf(B)) ** 2 / (2 * np.cosh(1) ** 4))
print(probs[2, 0, 0, 0])

######################################################################
# The PennyLane simulation results agree (with almost negligible numerical error) to the
# expected result from the Gaussian boson sampling equation!
#
# References
# ----------
#
# .. [#Arute2019]
#
#     Arute, F., Arya, K., Babbush, R. et al. "Quantum supremacy using a programmable
#     superconducting processor"
#     `Nature 574, 505-510 (2019) <https://doi.org/10.1038/s41586-019-1666-5>`__.
#
# .. [#Zhong2020]
#
#     Zhong, H.-S., Wang, H., Deng, Y.-H. et al. (2020). Quantum computational advantage using photons. Science, 10.1126/science.abe8770.
#
# .. [#hamilton2017]
#
#     Craig S. Hamilton, Regina Kruse, Linda Sansoni, Sonja Barkhofen, Christine Silberhorn,
#     and Igor Jex. Gaussian boson sampling. Physical Review Letters, 119:170501, Oct 2017.
#     arXiv:1612.01199, doi:10.1103/PhysRevLett.119.170501.
#
# .. [#lund2014]
#
#     A. P. Lund, A. Laing, S. Rahimi-Keshari, T. Rudolph, J. L. O’Brien, and T. C. Ralph.
#     Boson sampling from a gaussian state. Physical Review Letters, 113:100502, Sep 2014.
#     doi:10.1103/PhysRevLett.113.100502.
#
# .. [#aaronson2013]
#
#     Scott Aaronson and Alex Arkhipov. The computational complexity of linear optics. Theory of
#     Computing, 9(1):143–252, 2013. doi:10.4086/toc.2013.v009a004.
#
# .. [#tillmann2013]
#
#     Max Tillmann, Borivoje Dakić, René Heilmann, Stefan Nolte, Alexander Szameit, and Philip
#     Walther. Experimental boson sampling. Nature Photonics, 7(7):540–544, May 2013.
#     doi:10.1038/nphoton.2013.102.
#
# .. [#reck1994]
#
#     Michael Reck, Anton Zeilinger, Herbert J. Bernstein, and Philip Bertani. Experimental
#     realization of any discrete unitary operator. Physical Review Letters, 73(1):58–61, Jul 1994.
#     doi:10.1103/physrevlett.73.58.
#
# .. [#clements2016]
#
#     William R Clements, Peter C Humphreys, Benjamin J Metcalf, W Steven Kolthammer, and
#     Ian A Walsmley. Optimal design for universal multiport interferometers. Optica,
#     3(12):1460–1465, 2016. doi:10.1364/OPTICA.3.001460.
