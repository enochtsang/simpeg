import Utils, numpy as np, scipy.sparse as sp
from Tests import checkDerivative

class Model(np.ndarray):

    def __new__(cls, input_array, mapping=None):
        assert isinstance(mapping, IdentityMap), 'mapping must be a SimPEG.Mapping'
        obj = np.asarray(input_array).view(cls)
        obj._mapping = mapping
        if not obj.size == mapping.nP:
            raise Exception('Incorrect size for array.')
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self._mapping = getattr(obj, '_mapping', None)

    @property
    def mapping(self):
        return self._mapping

    @property
    def transform(self):
        if getattr(self, '_transform', None) is None:
            self._transform = self.mapping.transform(self.view(np.ndarray))
        return self._transform

    @property
    def transformDeriv(self):
        if getattr(self, '_transformDeriv', None) is None:
            self._transformDeriv = self.mapping.transformDeriv(self.view(np.ndarray))
        return self._transformDeriv

    def test(self, **kwargs):
        return self.mapping.test(self.view(np.ndarray),**kwargs)


class IdentityMap(object):
    """
    SimPEG Map

    """

    __metaclass__ = Utils.SimPEGMetaClass

    mesh = None      #: A SimPEG Mesh

    def __init__(self, mesh):
        self.mesh = mesh

    @property
    def nP(self):
        """
            :rtype: int
            :return: number of parameters in the model
        """
        return self.mesh.nC

    @property
    def shape(self):
        """
            The default shape is (mesh.nC, nP).

            :rtype: (int,int)
            :return: shape of the operator as a tuple
        """
        return (self.mesh.nC, self.nP)

    def transform(self, m):
        """
            Changes the model into the physical property.

            .. note::

                This can be called by the __mul__ property against a numpy.ndarray.

            :param numpy.array m: model
            :rtype: numpy.array
            :return: transformed model

        """
        return m

    def transformInverse(self, D):
        """
            Changes the physical property into the model.

            .. note::

                The *transformInverse* may not be easy to create in general.

            :param numpy.array D: physical property
            :rtype: numpy.array
            :return: model

        """
        raise NotImplementedError('The transformInverse is not implemented.')

    def transformDeriv(self, m):
        """
            The derivative of the transformation.

            :param numpy.array m: model
            :rtype: scipy.csr_matrix
            :return: derivative of transformed model

        """
        return sp.identity(m.size)

    def test(self, m=None, **kwargs):
        """Test the derivative of the mapping.

            :param numpy.array m: model
            :param kwargs: key word arguments of :meth:`SimPEG.Tests.checkDerivative`
            :rtype: bool
            :return: passed the test?

        """
        print 'Testing the %s Class!' % self.__class__.__name__
        if m is None:
            m = np.random.rand(self.nP)
        if 'plotIt' not in kwargs:
            kwargs['plotIt'] = False
        return checkDerivative(lambda m : [self.transform(m), self.transformDeriv(m)], m, **kwargs)

    def _assertMatchesPair(self, pair):
        assert (isinstance(self, pair) or
            isinstance(self, ComboMap) and isinstance(self.maps[0], pair)
            ), "Mapping object must be an instance of a %s class."%(pair.__name__)

    def __mul__(self, val):
        if isinstance(val, ComboMap):
            return ComboMap(self.mesh, [self] + val.maps)
        elif isinstance(val, IdentityMap):
            return ComboMap(self.mesh, [self, val])
        elif isinstance(val, np.ndarray):
            return self.transform(val)

class NonLinearMap(object):
    """
    SimPEG NonLinearMap

    """

    __metaclass__ = Utils.SimPEGMetaClass

    counter = None   #: A SimPEG.Utils.Counter object
    mesh = None      #: A SimPEG Mesh

    def __init__(self, mesh):
        self.mesh = mesh

    def transform(self, u, m):
        """
            :param numpy.array u: fields
            :param numpy.array m: model
            :rtype: numpy.array
            :return: transformed model

            The *transform* changes the model into the physical property.

        """
        return m

    def transformDerivU(self, u, m):
        """
            :param numpy.array u: fields
            :param numpy.array m: model
            :rtype: scipy.csr_matrix
            :return: derivative of transformed model

            The *transform* changes the model into the physical property.
            The *transformDerivU* provides the derivative of the *transform* with respect to the fields.
        """
        raise NotImplementedError('The transformDerivU is not implemented.')


    def transformDerivM(self, u, m):
        """
            :param numpy.array u: fields
            :param numpy.array m: model
            :rtype: scipy.csr_matrix
            :return: derivative of transformed model

            The *transform* changes the model into the physical property.
            The *transformDerivU* provides the derivative of the *transform* with respect to the model.
        """
        raise NotImplementedError('The transformDerivM is not implemented.')

    @property
    def nP(self):
        """Number of parameters in the model."""
        return self.mesh.nC

    def example(self):
        raise NotImplementedError('The example is not implemented.')

    def test(self, m=None):
        raise NotImplementedError('The test is not implemented.')


class ExpMap(IdentityMap):
    """SimPEG ExpMap"""

    def __init__(self, mesh, **kwargs):
        IdentityMap.__init__(self, mesh, **kwargs)

    def transform(self, m):
        """
            :param numpy.array m: model
            :rtype: numpy.array
            :return: transformed model

            The *transform* changes the model into the physical property.

            A common example of this is to invert for electrical conductivity
            in log space. In this case, your model will be log(sigma) and to
            get back to sigma, you can take the exponential:

            .. math::

                m = \log{\sigma}

                \exp{m} = \exp{\log{\sigma}} = \sigma
        """
        return np.exp(Utils.mkvc(m))


    def transformInverse(self, D):
        """
            :param numpy.array D: physical property
            :rtype: numpy.array
            :return: model

            The *transformInverse* changes the physical property into the model.

            .. math::

                m = \log{\sigma}

        """
        return np.log(Utils.mkvc(D))


    def transformDeriv(self, m):
        """
            :param numpy.array m: model
            :rtype: scipy.csr_matrix
            :return: derivative of transformed model

            The *transform* changes the model into the physical property.
            The *transformDeriv* provides the derivative of the *transform*.

            If the model *transform* is:

            .. math::

                m = \log{\sigma}

                \exp{m} = \exp{\log{\sigma}} = \sigma

            Then the derivative is:

            .. math::

                \\frac{\partial \exp{m}}{\partial m} = \\text{sdiag}(\exp{m})
        """
        return Utils.sdiag(np.exp(Utils.mkvc(m)))

class Vertical1DMap(IdentityMap):
    """Vertical1DMap

        Given a 1D vector through the last dimension
        of the mesh, this will extend to the full
        model space.
    """

    def __init__(self, mesh, **kwargs):
        IdentityMap.__init__(self, mesh, **kwargs)

    @property
    def nP(self):
        """Number of model properties.

           The number of cells in the
           last dimension of the mesh."""
        return self.mesh.vnC[self.mesh.dim-1]

    def transform(self, m):
        """
            :param numpy.array m: model
            :rtype: numpy.array
            :return: transformed model
        """
        repNum = self.mesh.vnC[:self.mesh.dim-1].prod()
        return Utils.mkvc(m).repeat(repNum)

    def transformDeriv(self, m):
        """
            :param numpy.array m: model
            :rtype: scipy.csr_matrix
            :return: derivative of transformed model
        """
        repNum = self.mesh.vnC[:self.mesh.dim-1].prod()
        repVec = sp.csr_matrix(
                    (np.ones(repNum),
                    (range(repNum), np.zeros(repNum))
                    ), shape=(repNum, 1))
        return sp.kron(sp.identity(self.nP), repVec)

class Mesh2Mesh(IdentityMap):
    """
        Takes a model on one mesh are translates it to another mesh.

    """

    def __init__(self, meshes, **kwargs):
        Utils.setKwargs(self, **kwargs)

        assert type(meshes) is list, "meshes must be a list of two meshes"
        assert len(meshes) == 2, "meshes must be a list of two meshes"
        assert meshes[0].dim == meshes[1].dim, """The two meshes must be the same dimension"""

        self.mesh  = meshes[0]
        self.mesh2 = meshes[1]

        self.P = self.mesh2.getInterpolationMat(self.mesh.gridCC,'CC',zerosOutside=True)

    @property
    def nP(self):
        """Number of parameters in the model."""
        return self.mesh2.nC
    def transform(self, m):
        return self.P*m
    def transformDeriv(self, m):
        return self.P


class ActiveCells(IdentityMap):
    """
        Active model parameters.

    """

    indActive   = None #: Active Cells
    valInactive = None #: Values of inactive Cells
    nC          = None #: Number of cells in the full model

    def __init__(self, mesh, indActive, valInactive, nC=None):
        self.mesh  = mesh

        self.nC = nC or mesh.nC

        if indActive.dtype is not bool:
            z = np.zeros(self.nC,dtype=bool)
            z[indActive] = True
            indActive = z
        self.indActive = indActive
        self.indInactive = np.logical_not(indActive)
        if Utils.isScalar(valInactive):
            valInactive = np.ones(self.nC)*float(valInactive)

        valInactive[self.indActive] = 0
        self.valInactive = valInactive

        inds = np.nonzero(self.indActive)[0]
        self.P = sp.csr_matrix((np.ones(inds.size),(inds, range(inds.size))), shape=(self.nC, self.nP))

    @property
    def nP(self):
        """Number of parameters in the model."""
        return self.indActive.sum()

    def transform(self, m):
        return self.P*m + self.valInactive
    def transformDeriv(self, m):
        return self.P

class ComboMap(IdentityMap):
    """Combination of various maps."""

    def __init__(self, mesh, maps, **kwargs):
        IdentityMap.__init__(self, mesh, **kwargs)

        self.maps = []
        for m in maps:
            if not isinstance(m, IdentityMap):
                self.maps += [m(mesh, **kwargs)]
            else:
                self.maps += [m]

    @property
    def nP(self):
        """Number of model properties.

           The number of cells in the
           last dimension of the mesh."""
        return self.maps[-1].nP

    def transform(self, m):
        for map_i in reversed(self.maps):
            m = map_i.transform(m)
        return m

    def transformDeriv(self, m):
        deriv = 1
        mi = m
        for map_i in reversed(self.maps):
            deriv = map_i.transformDeriv(mi) * deriv
            mi = map_i.transform(mi)
        return deriv

    def __mul__(self, val):
        if isinstance(val, ComboMap):
            return ComboMap(self.mesh, self.maps + val.maps)
        elif isinstance(val, IdentityMap):
            return ComboMap(self.mesh, self.maps + [val])
        elif isinstance(val, np.ndarray):
            return self.transform(val)

class ComplexMap(IdentityMap):
    """ComplexMap

        default nP is nC in the mesh times 2 [real, imag]

    """
    def __init__(self, mesh, nP=None):
        IdentityMap.__init__(self, mesh)
        if nP is not None:
            assert nP%2 == 0, 'nP must be even.'
        self._nP = nP or (self.mesh.nC * 2)

    @property
    def nP(self):
        return self._nP

    @property
    def shape(self):
        return (self.nP/2,self.nP)

    def transform(self, m):
        nC = self.mesh.nC
        return m[:nC] + m[nC:]*1j

    def transformDeriv(self, m):
        nC = self.nP/2
        shp = (nC, nC*2)
        def fwd(v):
            return v[:nC] + v[nC:]*1j
        def adj(v):
            return np.r_[v.real,v.imag]
        return Utils.SimPEGLinearOperator(shp,fwd,adj)

    transformInverse = transformDeriv

