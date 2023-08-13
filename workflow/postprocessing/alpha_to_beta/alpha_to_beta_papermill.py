import papermill as pm

for reg in range(1, 20):
    print(f'RGI reg {reg:02d}')
    pm.execute_notebook(
       'alpha_to_beta_tpl.ipynb',
       f'alpha_to_beta_RGI{reg:02d}.ipynb',
       parameters=dict(reg=reg),
       log_output=True
    )
print('DONE!')
