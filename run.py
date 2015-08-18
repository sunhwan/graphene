import os
for i in range(20):
    os.system('python build.py')
    os.system('cp graphene.pdb graphene_%d.pdb' % i)
