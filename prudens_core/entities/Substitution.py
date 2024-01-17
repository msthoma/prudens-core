from __future__ import annotations
from typing import Union, Dict, Set, Tuple, TYPE_CHECKING
from copy import deepcopy
from prudens_core.entities.Constant import Constant
from prudens_core.entities.Variable import Variable
from prudens_core.errors.RuntimeErrors import VariableNotFoundInSubstitutionError, DuplicateValueError
if TYPE_CHECKING:
    from prudens_core.entities.Literal import Literal

class Substitution:
    __slots__ = ("sub", "equivalent_variables")

    def __init__(self, other: Union[None, Substitution] = None) -> None:
        # The two dicts (should) have at any time disjoint sets of keys.
        if other == None:
            self.sub: Dict[Variable, Union[Variable, Constant]] = dict() # FIXME Why is this both Variable and Constant?
            self.equivalent_variables: Dict[Variable, Set[Variable]] = dict()
        else:
            self.sub: Dict[Variable, Union[Variable, Constant]] = other.sub
            self.equivalent_variables: Dict[Variable, Set[Variable]] = other.equivalent_variables

    def is_propositional(self) -> bool:
        return len(self.sub) == 0 and len(self.equivalent_variables) == 0

    def apply(self, literal: Literal) -> Literal:
        instance: Literal = deepcopy(literal)
        # print("self.sub:", self.sub)
        # print("self.equivalent_variables:", self.equivalent_variables)
        if self.is_propositional():
            # print("self.is_propositional() == True")
            # print("self.sub:", self.sub)
            return instance
        for i in range(len(instance.arguments)):
            argument = instance.arguments[i]
            if isinstance(argument, Variable):
                # print("argument is variable:", argument)
                # value: Union[Constant, Variable, None] = self.__apply(argument)
                # if value:
                #     instance.arguments[i] = value
                try:
                    value: Union[Constant, Variable, None] = self.__apply(argument)
                    instance.arguments[i] = value
                except VariableNotFoundInSubstitutionError:
                    # print("VariableNotFoundInSubstitutionError")
                    pass
        # for i, value in sub_indices.items():
        #     instance.arguments[i] = value
        # print("instance before return:", [str(x) for x in instance.arguments])
        return instance

    def __apply(self, variable: Variable) -> Union[Constant, Variable, None]:
        """
        There is also an alternative approach. You use indices to map variables to other stuff
        (i.e., variables or constants) so that the application step is time consuming while the extension step 
        is trivial.
        """
        try:
            return self.sub[variable]
        except KeyError:
            raise VariableNotFoundInSubstitutionError(variable)
    
    def extend(self, other: Union[Substitution, Tuple[Variable, Constant]]) -> None:
        if isinstance(other, tuple):
            self.__extend(other[0], other[1])
            return
        for variable, value in other.sub.items():
            try:
                self.__extend(variable, value)
            except DuplicateValueError as e:
                raise e
        for var1, vars in other.equivalent_variables.items():
            for var2 in vars:
                try:
                    self.__extend(var1, var2)
                except DuplicateValueError as e:
                    raise e

    def __extend(self, variable: Variable, value: Union[Variable, Constant]) -> None:
        # Consider returning the new sub (is this OO, though?)
        # Extend self.sub by variable: value and raise relevant errors when needed (e.g., inconsistent extension)
        if isinstance(value, Constant):
            try:
                self.__extend_by_constant(variable, value)
            except DuplicateValueError as e:
                raise e
        else:
            self.__extend_by_variable(variable, value)

    def __extend_by_constant(self, variable: Variable, value: Constant) -> None:
        if variable in self.equivalent_variables.keys():
            vars: Set[Variable] = self.equivalent_variables[variable]
            for variable in vars:
                self.sub[variable] = value
                del self.equivalent_variables[variable]
        elif variable not in self.sub.keys():
            self.sub[variable] = value
        elif self.sub[variable] != value:
            raise DuplicateValueError(variable, self.sub[variable], value)
            
    def __extend_by_variable(self, variable: Variable, value: Variable) -> None:
        # print(f"self.sub: {self.sub}\n\tvalue: {value},\n\ttype(value): {type(value)}")
        if variable in self.sub.keys():
            self.extend_by_constant(value, self.sub[variable])
        elif value in self.sub.keys():
            self.extend_by_constant(variable, self.sub[value])
        elif variable in self.equivalent_variables.keys():
            self.equivalent_variables[variable].add(value)
            for var in self.equivalent_variables[variable]:
                self.equivalent_variables[var] = self.equivalent_variables[variable]
        elif value in self.equivalent_variables.keys():
            self.equivalent_variables[value].add(variable)
            for var in self.equivalent_variables[value].add(variable):
                self.equivalent_variables[var] = self.equivalent_variables[value]
        else:
            self.equivalent_variables[variable] = set([variable, value])
            self.equivalent_variables[value] = set([value, variable])

    def to_code(self) -> str:
        code_string: str = ""
        for key, val in self.sub.items():
            code_string += str(key) + "=" + str(val) + "\n"
        return code_string
    
    def __bool__(self) -> bool:
        return True
    
    def __str__(self) -> str:
        sub_str: str = ""
        for variable, value in self.sub.items():
            sub_str += str(variable) + " -> " + str (value) + "; "
        included: Set[Tuple[Variable, Variable]] = set()
        for var_1, vars in self.equivalent_variables.items():
            for var_2 in vars:
                if (var_1, var_2) in included or (var_2, var_1) in included:
                    continue
                included.add((var_1, var_2))
                sub_str += str(var_1) + " <-> " + str(var_2) + "; "
        return sub_str.strip()

    def __deepcopy__(self, memodict = {}) -> Substitution:
        copycat: Substitution = Substitution()
        copycat.sub = { k: v for k, v in self.sub.items() }
        copycat.equivalent_variables = { k: v for k, v in self.equivalent_variables.items() }
        return copycat

    def __eq__(self, other: Substitution) -> bool:
        if not isinstance(other, Substitution):
            return False
        if self.is_propositional() and other.is_propositional():
            return True
        return self.sub == other.sub and self.equivalent_variables == other.equivalent_variables

    def __hash__(self) -> int:
        return hash(self.__str__())
    # FIXME To be fixed according to __eq__()