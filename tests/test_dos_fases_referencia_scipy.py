"""Verificación opcional: SciPy/HiGHS es un oráculo, no el motor de la app.

Sin SciPy se omite únicamente esta prueba. No hace falta instalarlo para usar
el módulo o ejecutar las 29 pruebas principales.
"""
import random
import unittest
from fractions import Fraction
from blueprints.dos_fases_solver import solve
try:
    from scipy.optimize import linprog
except ImportError:
    linprog=None


class ReferenceTests(unittest.TestCase):
    @unittest.skipIf(linprog is None, "Comparación opcional: requiere scipy")
    def test_300_models_against_highs(self):
        rng=random.Random(20261101)
        for case in range(300):
            n=rng.randint(1,5);m=rng.randint(1,8)
            c=[rng.randint(-7,9) for _ in range(n)];sense=rng.choice(['max','min'])
            constraints=[];aub=[];bub=[];aeq=[];beq=[]
            for _ in range(m):
                a=[rng.randint(-5,6) for _ in range(n)]
                op=rng.choice(['<=','<=','>=','=']);b=rng.randint(-12,25)
                constraints.append(dict(coefficients=a,operator=op,rhs=b))
                if op=='=':aeq.append(a);beq.append(b)
                else:
                    s=-1 if op=='>=' else 1;aub.append([s*x for x in a]);bub.append(s*b)
            sign=-1 if sense=='max' else 1
            ref=linprog([sign*v for v in c],A_ub=aub or None,b_ub=bub or None,
                        A_eq=aeq or None,b_eq=beq or None,method='highs',options={'presolve':False})
            result=solve(dict(sense=sense,objective=c,constraints=constraints))
            with self.subTest(case=case):
                self.assertEqual(result['status'],{0:'optimal',2:'infeasible',3:'unbounded'}.get(ref.status))
                if ref.status==0:
                    self.assertAlmostEqual(float(Fraction(result['objective_value'])),sign*ref.fun,places=6)


if __name__=='__main__':unittest.main()
