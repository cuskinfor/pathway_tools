import dai
import pathway_tools.dai_conf

class FactorCalculator:

    def calculate(self, *args, **kw):
        raise Exception("Unimplemented method 'calculate'")


class Variable:
    def __init__(self, variable_name, variable_type, variable_id, dim):
        self.variable_name = variable_name
        self.variable_type = variable_type
        self.dim = dim
        self.variable_id = variable_id
        self.dai_value = None

    def __str__(self):
        return "<pathway_tools.dai_util.Variable name=%s type=%s id=%d 0x%s>" % (
            self.variable_name, self.variable_type, self.variable_id,
            id(self)
        )

    def __repr__(self):
        return self.__str__()

class Factor:
    def __init__(self, factor_name, factor_type, factor_id, variables):
        self.factor_name = factor_name
        self.factor_type = factor_type
        self.factor_id = factor_id
        self.variables = variables

    def __str__(self):
        return "<pathway_tools.dai_util.Factor name=%s type=%s id=%s vars=%s 0x%s>" % (
            self.factor_name,
            self.factor_type,
            self.factor_id,
            ",".join( str(a) for a in self.variables ),
            id(self)
        )


class VariableMap:
    def __init__(self):
        #from label/type tuple to PathwayVariable object
        self.variable_map = {}
        #from variable ID to PathwayVariable object
        self.varid_map = {}
        self.var_count = 0

    def get_or_add_variable(self, label, elem_type, dim):
        tup = (label, elem_type)
        if tup in self.variable_map:
            return self.variable_map[tup]
        var = Variable(label, elem_type, self.var_count, dim)
        self.var_count += 1
        self.__insert(var)
        return var

    def __insert(self, pv):
        self.variable_map[ (pv.variable_name, pv.variable_type) ] = pv
        self.varid_map[ pv.variable_id ] = pv

    def get_variable_by_id(self, v):
        return self.varid_map[v]

    def has_variable_by_label(self, label, elem_type):
        return (label, elem_type) in self.variable_map

    def get_variable_by_label(self, label, elem_type):
        try:
            return self.variable_map[ (label, elem_type) ]
        except KeyError:
            return None

    def list_variables(self, label, elem_type):
        for v_label, v_elem_type in self.variable_map:
            if label is None or v_label == label:
                if elem_type is None or v_elem_type == elem_type:            
                    yield self.variable_map[ (v_label, v_elem_type) ]

    def __len__(self):
        return len(self.variable_map)

    def __iter__(self):
        for i in sorted(self.varid_map):
            yield self.varid_map[i]


class FactorMap:
    def __init__(self):
        self.factor_map = {}
        self.factor_id_map = {}

    def add_factor(self, factor_name, factor_type, variables):
        l = (factor_name, factor_type)
        if l in self.factor_map:
            raise Exception("Need unique name for CPTGenerator")
        fid = len(self.factor_map)
        factor = Factor(factor_name, factor_type, fid, variables)
        self.factor_map[l] = factor
        self.factor_id_map[fid] = factor
        return factor

    def list_factors(self, factor_name, factor_type):
        for v_label, v_type in self.factor_map:
            if factor_name is None or v_label == factor_name:
                if factor_type is None or v_type == factor_type:            
                    yield self.factor_map[ (v_label, v_type) ]

    def __iter__(self):
        for i in sorted(self.factor_id_map):
            yield self.factor_id_map[i]


class MultiDimMatrix(object):
    """
    From http://stackoverflow.com/questions/508657/multidimensional-array-in-python/508677#508677
    """
    def __init__(self, *dims):
        self._shortcuts = [i for i in self._create_shortcuts(dims)]
        self._li = [None] * (self._shortcuts.pop())
        #self._shortcuts.reverse()

    def _create_shortcuts(self, dims):
        dimList = list(dims)
        #dimList.reverse()
        number = 1
        yield 1
        for i in dimList:
            number *= i
            yield number

    def _flat_index(self, index):
        if len(index) != len(self._shortcuts):
            raise TypeError()

        flatIndex = 0
        for i, num in enumerate(index):
            flatIndex += num * self._shortcuts[i]
        return flatIndex

    def __getitem__(self, index):
        return self._li[self._flat_index(index)]

    def __setitem__(self, index, value):
        self._li[self._flat_index(index)] = value

    def __str__(self):
        return "%s" % (self._li)


class VectorRemap:
    def __init__(self, order):
        self.order = order

    def remap(self, val):
        out = [None] * len(self.order)
        for s, d in enumerate(self.order):
            out[s] = val[d]
        return out


class CPT:
    """
    CPT 

    Conditional Probablity Table

    This class stores a set of variables (and their dimensions) as well
    as the multidimensional matrix that represents the their probablities.

    Methods for normalizing the table against different variables should go here
    """
    def __init__(self, variables, dims):
        self.variables = variables
        self.dims = dims
        self.varmap = {}
        for i, v in enumerate(variables):
            self.varmap[v] = i
        self._table = MultiDimMatrix(*dims)

    def __str__(self):
        #num_vars = len(self.variables)
        #fac_states = [ 0 ] * num_vars
        #return "%s" % ("\n".join(str(i) for i in self._table._li))
        out = []
        i = 0
        for v in multi_dim_iter(self.dims):
            out.append("%d %f # %s" % (i, self._table.__getitem__(v), v ))
            i += 1
        return "\n".join(out)

    def iter():
        for i in multi_dim_iter(self.dims):
            yield i

    def __len__(self):
        out = 1
        for i in self.dims:
            out *= i
        return out

    def set_value(self, value, factors):
        idx = []
        for i in self.variables:
            idx.append( factors[i] )
        self._table.__setitem__(idx, value)

    def cpt_linear_table(self, variable_set=None):
        if variable_set is None:
            variable_set = self.variables

        num_vars = len(variable_set)

        dims = []
        remap = []
        for v in variable_set:
            dims.append(self.dims[self.varmap[v]])
            remap.append(self.variables.index(v))
        out = MultiDimMatrix(*dims)
        remap = VectorRemap(remap)
        for fac_states in multi_dim_iter(self.dims):
            out[ remap.remap(fac_states) ] = self._table[fac_states]
        return out._li


class CPTGenerator:
    """
    CPT 

    Conditional Probablity Table

    This class stores a set of variables (and their dimensions) as well
    as the multidimensional matrix that represents the their probablities.

    Methods for normalizing the table against different variables should go here
    """
    def __init__(self, variables, calculator, cpt_name, cpt_type):
        self.variables = variables
        self.calculator = calculator
        self.cpt_name = cpt_name
        self.cpt_type = cpt_type

    def __str__(self):
        return self.cpt_name + ":" + self.cpt_type
        #num_vars = len(self.variables)
        #fac_states = [ 0 ] * num_vars
        #return "%s" % ("\n".join(str(i) for i in self.table._li))

    def get_variable_ids(self):
        for var in self.variables:
            yield var.variable_id

    def get_variable_by_id(self, id):
        for var in self.variables:
            if var.variable_id == id:
                return var
        return None

    def generate(self, variable_set=None):
        """
        Generate a CPT based on the variable_set (by default all the variables that where used
        to intialize the CPTGenerator), and the CPTPair rules that apply.
        """
        if variable_set is None:
            variable_set = sorted(self.get_variable_ids())

        num_vars = len(variable_set)
        fac_states = [ 0 ] * num_vars
        fac_index = 0
        fac_values = []

        var_list = []
        var_dims = []
        for i in variable_set:
            d = self.get_variable_by_id(i).dim
            var_list.append(i)
            var_dims.append(d)

        cpt = CPT(var_list, var_dims)
        done = False
        while not done and fac_states[-1] < var_dims[-1]:
            c_map = {}
            for i, v in enumerate(variable_set):
                c_map[v] = fac_states[i]
            val = self.calculator.calculate(c_map)
            if val is None:
                raise Exception("Null value from factor calculator")
            cpt.set_value(val, c_map)
            inc_index = 0
            fac_states[inc_index] += 1
            while fac_states[inc_index] >= self.get_variable_by_id(variable_set[inc_index]).dim:
                fac_states[inc_index] = 0
                inc_index += 1
                if inc_index > len(fac_states)-1:
                    done = True
                    break
                fac_states[inc_index] += 1
        return cpt


def multi_dim_iter(dims):
    states = [0] * len(dims)
    done = False
    while not done and states[-1] < dims[-1]:
        yield states
        inc_index = 0
        states[inc_index] += 1
        while states[inc_index] >= dims[inc_index]:
            states[inc_index] = 0
            inc_index += 1
            if inc_index > len(states)-1:
                done = True
                break
            states[inc_index] += 1



class FactorGraph:
    """
    FactorGraph

    The FactorGraph represents all of the various data elements needed
    to setup a Factor graph calculation. It contains factor variable mappings, 
    and CPT definitions
    """
    def __init__(self):
        self.var_map = VariableMap()
        self.factor_map = FactorMap()
        self.cpt_gen_map = {}

    def append_cpt(self, cpt):
        cid = self.factor_map.add_factor(cpt.cpt_name, cpt.cpt_type, cpt.variables)
        self.cpt_gen_map[cid] = cpt
        
    def describe(self):

        #yield "# Variables"
        for path_var in self.var_map:
            yield "# %d\t%s\t%s" % (path_var.variable_id, path_var.variable_name, path_var.variable_type)

        yield "## Factor Graphs"
        yield "%s" % (len(self.cpt_gen_map))

        for cpt_id in self.cpt_gen_map:
            cpt = self.cpt_gen_map[cpt_id]
            node_order = []
            node_dim   = []

            for n in sorted(cpt.get_variable_ids()):
                node_order.append(n)
                node_dim.append(cpt.get_variable_by_id(n).dim)

            yield "## CPT %s %s " % (cpt.cpt_name, cpt.cpt_type)
            yield "%s" % (len(node_order))
            yield " ".join([str(i) for i in node_order])
            yield " ".join([str(i) for i in node_dim])
            table = cpt.generate(node_order)
            yield "%s" % (len(table))
            yield "%s" % (table)

    def generate_dai_factor_graph(self):
        cpt_map = {}
        for factor in self.factor_map:
            cpt_gen = self.cpt_gen_map[factor]
            elem = cpt_gen.generate()
            cpt_map[factor] = elem
        return DaiFactorGraph(self.var_map, self.factor_map, cpt_map)

class SharedParameters:
    def __init__(self, variable_set_labels):
        self.variable_set_labels = variable_set_labels
        self.shared_list = []
        self.variable_dims = None
        self.result = None

    def add_factor(self, variable_list, factor):
        if len(variable_list) != len(self.variable_set_labels):
            raise Exception("Mismatch Variable set size added")
        self.shared_list.append( (variable_list, factor) )
        if self.variable_dims is None:
            self.variable_dims = []
            for v in variable_list:
                self.variable_dims.append(v.dim)


    def __str__(self):
        out = " ".join(self.variable_set_labels) + "\n"
        for state in multi_dim_iter(self.variable_dims):
            out += " ".join( str(i) for i in state)
            pos = 0
            dim = 1
            for i, v in enumerate(state):
                pos += v * dim
                dim *= self.variable_dims[i]
            if self.result is not None:
                out += "\t" + str(self.result[pos])
            out += "\n"
        return out

class DaiEM:
    def __init__(self, dai_factor_graph):
        self.dai_factor_graph = dai_factor_graph
        self.ev = dai.Evidence()
        self.shared_param_list = []
        self.evidence_map = {}

    def add_evidence(self, sample, variable, value):
        if sample not in self.evidence_map:
            self.evidence_map[sample] = {}
        self.evidence_map[sample][variable] = value

    def new_shared(self, variable_set_labels):
        param = SharedParameters(variable_set_labels)
        self.shared_param_list.append(param)
        return param

    def __iter__(self):
        for i in self.shared_param_list:
            yield i

    def run(self, method_name, pseudo_count=0.1, **kwds):
        self.dai_factor_graph.setup_factor_graph()
        obsvec = dai.ObservationVec()
        for sample in self.evidence_map:
            obs = dai.Observation()
            for var in self.evidence_map[sample]:
                #obs[ self.factor_graph.var_map[var].dai_variable ] = self.evidence_map[sample][var]
                #obs[ var.get_dai_value() ] = self.evidence_map[sample][var]
                obs[ self.dai_factor_graph.dai_variables[var] ] = self.evidence_map[sample][var]
            obsvec.append(obs)

        sp_vec = dai.VecSharedParameters()
        for sp in self.shared_param_list:
            fo = dai.FactorOrientations()
            for variable_list, factor in sp.shared_list:
                vec = dai.VecVar()
                for v in variable_list:
                    vec.append(self.dai_factor_graph.dai_variables[v])
                fo[factor.factor_id] = vec

            total_dim = 1
            for d in sp.variable_dims:
                total_dim *= d
            #props = dai.PropertySet()
            #props["total_dim"] = str(total_dim)
            #props["target_dim"] = str(sp.variable_dims[0])
            #pe = dai.ParameterEstimation.construct("CondProbEstimation", props)
            pseudo_counts = dai.Prob(total_dim, pseudo_count)
            #for i in range(total_dim):
            #    pseudo_count.append( 0.01 )
            pe = dai.CondProbEstimation(sp.variable_dims[0], pseudo_counts)
            dai_sp = dai.SharedParameters(fo, pe)
            sp_vec.append(dai_sp)

        max_step = dai.MaximizationStep(sp_vec)
        vec_max_step = dai.VecMaximizationStep()
        vec_max_step.append(max_step)
        evidence = dai.Evidence(obsvec)
        #inf_alg = self.factor_graph.get_inf_bp(verbose=True)
        prop = dai.PropertySet()
        for k in kwds:
            prop[k] = str(kwds[k])

        inf_alg = dai.newInfAlg(method_name, self.dai_factor_graph.get_factor_graph(), prop )
        em_props= dai.PropertySet()
        dai_em_alg = dai.EMAlg(evidence, inf_alg, vec_max_step, em_props)

        while not dai_em_alg.hasSatisfiedTermConditions():
            print "Cycle 1"
            l = dai_em_alg.iterate()
            if kwds.get("verbose", False):
                print "Iteration ", dai_em_alg.Iterations(), " likelihood: ", l
                for max_step in dai_em_alg:
                    print max_step, len(max_step)
                    for shared_param in max_step:
                        print "\t", shared_param.currentExpectations()
                        print "\t", shared_param.getPEst().estimate(shared_param.currentExpectations())
        
        for i in range(len(dai_em_alg[0])):
            shared_param = dai_em_alg[0][i]
            param_vec = shared_param.getPEst().estimate(shared_param.currentExpectations())
            var_list = self.shared_param_list[i].variable_set_labels
            var_dims = self.shared_param_list[i].variable_dims
            self.shared_param_list[i].result = param_vec
      

class DaiFactorGraph:
    def __init__(self, variable_map, factor_map, cpt_map):
        self.variable_map = variable_map
        self.factor_map = factor_map
        self.cpt_map = cpt_map
        self.dai_variables = {}
        self.vecfac = None

    def setup_factor_graph(self):
        self.vecfac = dai.VecFactor()
        elem_map = {}
        for elem in self.variable_map:
            if elem.variable_name not in elem_map:
                elem_map[ elem.variable_name ] = { elem.variable_type : elem.variable_id }
            else:
                elem_map[ elem.variable_name ][elem.variable_type] = elem.variable_id
            #dai_var_map[elem.variable] = dai.Var(elem.variable, elem.dim)


        for cpt in sorted(self.cpt_map.keys(), key=lambda x: x.factor_id ):
            cpt_value = self.cpt_map[cpt]
            var_list = dai.VarSet()
            v_list = list(cpt_value.variables)
            v_list.sort()
            for v_id in v_list:
                v = self.variable_map.get_variable_by_id(v_id)
                if v not in self.dai_variables:
                    self.dai_variables[v] = dai.Var(v.variable_id, v.dim)
                var_list.append(self.dai_variables[v])
            dai_factor = dai.Factor(var_list)
            for i, v in enumerate(cpt_value.cpt_linear_table()):
                dai_factor[i] = v
            self.vecfac.append(dai_factor)

    def setup_em(self):
        return DaiEM(self)

    def get_factor_graph(self):
        if self.vecfac is None:
            self.setup_factor_graph()
        return dai.FactorGraph(self.vecfac)

    def get_inf(self, name, **kwds):
        """
        cls, config = network_toolkit.dai_conf.config_map[name]
        prop = dai.PropertySet()
        for c in config:
            prop[c] = config[c]
        if verbose:
            prop["verbose"] = "1"
        sn = dai.FactorGraph(self.vecfac)
        inf = cls(sn, prop)
        return inf
        """

        sn = self.get_factor_graph()
        prop = dai.PropertySet()
        for k in kwds:
            prop[k] = str(kwds[k])
        inf_alg = dai.newInfAlg(name, sn, prop )
        return inf_alg

    def get_inf_jtree(self):
        sn = self.get_factor_graph()
        prop = dai.PropertySet()
        prop["inference"] = "SUMPROD"
        prop["updates"] = "HUGIN"
        prop["verbose"] = "1"
        inf = dai.JTree(sn, prop)
        return inf

    def get_inf_bp(self, logdomain=False, verbose=False):
        sn = dai.FactorGraph(self.vecfac)
        prop = dai.PropertySet()
        prop["tol"] = "1e-9"
        if logdomain:
            prop["logdomain"] = "1"
        else:
            prop["logdomain"] = "0"
        prop["updates"] = "SEQFIX"
        if verbose:
            prop["verbose"] = "1"
        else:
            prop["verbose"] = "0"
        lb_inf = dai.BP(sn, prop)
        return lb_inf

    def variables(self):
        for var in self.variable_map:
            yield var


