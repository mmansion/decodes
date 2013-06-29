from decodes.core import *
from . import dc_base, dc_vec, dc_point, dc_cs, dc_line, dc_mesh, dc_pgon, dc_curve
if VERBOSE_FS: print "surface.py loaded"



class Surface(IsParametrized):
    """
    a simple surface class

    to construct a surface, pass in a function and [optionally] two intervals that determine the a valid range of u&v values
    the function should expect two parameters u and v (float), and return a Point.

    """
    
    def __init__(self, function=None, dom_u=Interval(0,1), dom_v=Interval(0,1), tol_u=None, tol_v=None):
        """ Constructs a Curve object. If tolerance is None, Curve.tol = tol_max().
        
            :param function: A function returning points.
            :type function: function
            :param domain: Domain for curve points.
            :type domain: Interval
            :param tolerance: The tolerance of this Surface expressed in domain space
            :type tolerance: float
            :result: Surface object.
            :rtype: Surface
        """
        if function is not None : self._func = function
        self._dom = dom_u, dom_v
        self._tol = self.tol_max
        if tol_u is not None : self.tol_u = tol_u
        if tol_v is not None : self.tol_v = tol_v

        for u,v in [(self.u0,self.v0),(self.u0,self.v1),(self.u1,self.v1),(self.u1,self.v0)]:
            try:
                pt = self.func(u,v)
                pt.x
                pt.y
                pt.z
            except:
                raise GeometricError("Surface not valid: The given function does not return a point or plane at parameter %s, %s"%(u,v))
                    
        self._rebuild_surrogate()


    @property
    def domain_u(self): 
        """
        Returns the Interval domain for the U-direction of this Surface
            :result: Domain of this Surface in the U-direction.
            :rtype: Interval
        """
        return self._dom[0]

    @property
    def u0(self):
        """
        Returns the minimum value for the U domain of this Surface
        """
        return self._dom[0].a

    @property
    def u1(self):
        """
        Returns the maximum value for the U domain of this Surface
        """
        return self._dom[0].b

    @property
    def v0(self):
        """
        Returns the minimum value for the U domain of this Surface
        """
        return self._dom[1].a

    @property
    def v1(self):
        """
        Returns the maximum value for the U domain of this Surface
        """
        return self._dom[1].b

    @property
    def domain_v(self): 
        """
        Returns the Interval domain for the V-direction of this Surface
            :result: Domain of this Surface in the V-direction.
            :rtype: Interval
        """
        return self._dom[1]

    @property
    def tol_max(self):
        """Determines the maximium tolerance as Surface.domain_u.delta / 10 , Surface.domain_v.delta / 10
        """
        return [self._dom[0].delta / 10.0, self._dom[1].delta / 10.0]

    @property
    def tol_u(self):
        """
        """
        return self._tol[0]

    @tol_u.setter
    def tol_u(self, tolerance):
        self._tol[0] = tolerance
        if self._tol[0] > self.tol_max[0] :  self._tol[0] = self.tol_max[0]
        self._rebuild_surrogate()

    @property
    def tol_u_nudge(self):
        return self.tol_u/100.0

    @property
    def tol_v(self):
        """
        """
        return self._tol[1]

    @tol_v.setter
    def tol_v(self, tolerance):
        self._tol[1] = tolerance
        if self._tol[1] > self.tol_max[1] :  self._tol[1] = self.tol_max[1]
        self._rebuild_surrogate()

    @property
    def tol_v_nudge(self):
        return self.tol_v/100.0


    def deval(self,u,v):
        """ Evaluates this Surface and returns a Plane.
        T is a float value that falls within the defined domain of this Curve.
        Tangent vector determined by a nearest neighbor at distance Curve.tol/100

            :param u: U-value to evaluate the Surface at.
            :type t: float
            :param v: V-value to evaluate the Surface at.
            :type t: float
            :result: Plane.
            :rtype: Plane
        """
        '''
        # some rounding errors require something like this:
        if u < self.u0 and u > self.u0-self.tol_u : u = u0
        if u > self.u1 and u < self.u1+self.tol_u : u = u1
        if v < self.v0 and v > self.v0-self.tol_v : v = v0
        if v > self.v1 and v < self.v1+self.tol_v : v = v1
        '''
        if u<self.u0 or u>self.u1 : raise DomainError("Surface evaluated outside the bounds of its u-domain: deval(%s) %s"%(u,self.domain_u))
        if v<self.v0 or v>self.v1 : raise DomainError("Surface evaluated outside the bounds of its v-domain: deval(%s) %s"%(v,self.domain_v))
        
        pt,vec_u,vec_v = self._nudged(u,v)
        vec = vec_u.cross(vec_v)

        return Plane(pt, vec)

    def eval(self,u,v):
        """ Evaluates this Curve and returns a Plane.
        T is a normalized float value (0->1) which will be remapped to the domain defined by this Curve.
        equivalent to Curve.deval(Interval.remap(t,Interval(),Curve.domain))
            :param t: Normalized value between 0 and 1, to evaluate a curve.
            :type t: float
            :result: Plane.
            :rtype: Plane
        """
        if u<0 or u>1 : raise DomainError("u out of bounds.  eval() must be called numbers between 0->1: eval(%s)"%u)
        if v<0 or v>1 : raise DomainError("v out of bounds.  eval() must be called numbers between 0->1: eval(%s)"%v)
        return self.deval(Interval.remap(u,Interval(),self.domain_u),Interval.remap(v,Interval(),self.domain_v))




    def deval_curvature(self,u,v,calc_extras=False):
        # returns curvature values and osc circles
        pt, u_pos, u_neg, v_pos, v_neg = self._nudged(u,v,True)

        # if given a surface edge, nudge vectors a bit so we don't get zero curvature, but leave origin the same
        if (u-self.tol_u_nudge <= self.domain_u.a):
            nudged = self._nudged(self.tol_u_nudge,v,True)
            u_pos = nudged[1]
            u_neg = nudged[2]
        if (u+self.tol_u_nudge >= self.domain_u.b):
            nudged = self._nudged(self.domain_u.b-self.tol_u_nudge,v,True)
            u_pos = nudged[1]
            u_neg = nudged[2]

        if (v-self.tol_v_nudge <= self.domain_v.a):
            nudged = self._nudged(u,self.tol_v_nudge,True)
            v_pos = nudged[3]
            v_neg = nudged[4]
        if (v+self.tol_v_nudge >= self.domain_v.b):
            nudged = self._nudged(u,self.domain_v.b-self.tol_v_nudge,True)
            v_pos = nudged[3]
            v_neg = nudged[4]

        crv_u = Curve._curvature_from_vecs(pt,u_pos,u_neg,calc_extras)
        crv_v = Curve._curvature_from_vecs(pt,v_pos,v_neg,calc_extras)
        
        if calc_extras : return crv_u[0]*crv_v[0], (crv_u[0],crv_v[0]),(crv_u[1],crv_v[1])
        return crv_u,crv_v


    def eval_curvature(self,u,v,calc_extras=False):
        """
        """
        if u<0 or u>1 : raise DomainError("u out of bounds.  eval_curvature() must be called numbers between 0->1: eval(%s)"%u)
        if v<0 or v>1 : raise DomainError("v out of bounds.  eval_curvature() must be called numbers between 0->1: eval(%s)"%v)
        return self.deval_curvature(Interval.remap(u,Interval(),self.domain_u),Interval.remap(v,Interval(),self.domain_v),calc_extras)

    def deval_gauss(self,u,v):
        crvtr = self.deval_curvature(u,v)
        return crvtr[0] * crvtr[1]

    def eval_gauss(self,u,v):
        """
        """
        if u<0 or u>1 : raise DomainError("u out of bounds.  eval_gauss() must be called numbers between 0->1: eval(%s)"%u)
        if v<0 or v>1 : raise DomainError("v out of bounds.  eval_gauss() must be called numbers between 0->1: eval(%s)"%v)
        return self.deval_gauss(Interval.remap(u,Interval(),self.domain_u),Interval.remap(v,Interval(),self.domain_v))


    def _nudged(self,u,v,include_negs = False):
        #nearest neighbors along u and v axis of point(u,v); used for discrete approximations calculations 
        if u<self.domain_u.a or u>self.domain_u.b : raise DomainError("Curve evaluated outside the bounds of its u domain: deval(%s) %s"%(u,self.domain_u))
        if v<self.domain_v.a or v>self.domain_v.b : raise DomainError("Curve evaluated outside the bounds of its v domain: deval(%s) %s"%(v,self.domain_v))
        pt = Point(self.func(u,v))
        
        vec_u = False
        vec_ui = False
        if (u+self.tol_u_nudge <= self.domain_u.b): 
            vec_u = Vec(pt,self.func(u + self.tol_u_nudge,v))
        else:
            vec_ui = Vec(pt,self.func(u - self.tol_u_nudge,v))
            vec_u = vec_ui.inverted()

        vec_v = False
        vec_vi = False
        if (v+self.tol_v_nudge <= self.domain_v.b): 
            vec_v = Vec(pt,self.func(u,v + self.tol_v_nudge))
        else:
            vec_vi = Vec(pt,self.func(u,v - self.tol_v_nudge))
            vec_v = vec_vi.inverted()

        if not include_negs : return pt,vec_u,vec_v

        if not vec_ui: 
            if (u-self.tol_u_nudge >= self.domain_u.a): vec_ui = Vec(pt,self.func(u - self.tol_u_nudge,v))
            else : vec_ui = vec_u.inverted()
        if not vec_vi: 
            if (v-self.tol_v_nudge >= self.domain_v.a): vec_vi = Vec(pt,self.func(u,v - self.tol_v_nudge))
            else : vec_vi = vec_v.inverted()

        return pt,vec_u,vec_ui,vec_v,vec_vi



    def _rebuild_surrogate(self):
        self._surrogate = self.to_mesh()

    def to_mesh(self,do_close=False,divs_u=False,divs_v=False):
        msh = Mesh()
        if not divs_u : divs_u = int(math.ceil(self.domain_u.delta/self.tol_u))
        if not divs_v : divs_v = int(math.ceil(self.domain_v.delta/self.tol_v))
        u_vals = self.domain_u.divide((divs_u),True)
        v_vals = self.domain_v.divide((divs_v),True)

        
        for v in v_vals:
            for u in u_vals:
                msh.append(self._func(u,v))
        
        res_u = len(u_vals)
        # simple triangulation style
        for v in range(len(v_vals)):
            row = v*res_u
            for u in range(len(u_vals)-1):
                pi_0 = row+u
                pi_1 = row+u+1
                pi_2 = row+u+res_u+1
                pi_3 = row+u+res_u
                msh.add_face(pi_0,pi_1,pi_2,pi_3)
            if do_close:
                #last two faces in the row
                pi_0 = row+res_u-1
                pi_1 = row+0
                pi_2 = row+res_u
                pi_3 = row+res_u-1+res_u
                msh.add_face(pi_0,pi_1,pi_2,pi_3)
        
        return msh

    def isocurve(self, u_val=None, v_val=None):
        if u_val is None and v_val is None: raise AttributeError("Surface.isocurve requires either u_val OR v_val to be set")
        if u_val is not None and v_val is not None: raise AttributeError("u_val AND v_val cannot both be set when generating a Surface.isocurve")

        if v_val is None:
            if u_val<self.u0 or u_val>self.u1 : raise DomainError("Isocurve cannot be generated outside the bounds of this Surface's u-domain (%s) %s"%(u_val,self.domain_u))
            def iso_func(t):  return Point(self.func(u_val,t))
            return Curve(iso_func,self.domain_u,self.tol_u)
        else :
            if v_val<self.v0 or v_val>self.v1 : raise DomainError("Isocurve cannot be generated outside the bounds of this Surface's v-domain (%s) %s"%(v_val,self.domain_v))
            def iso_func(t): return Point(self.func(t,v_val))
            return Curve(iso_func,self.domain_v,self.tol_v)
