# mms-curvature
Python3 routines for calculating the magnetic field curvature at the mesocenter of the MMS fleet in tetrahedron formation.

Also contains basic functions for loading various instrument data from MMS spacecraft, calculating spacial gradients over time, and deriving the curl and divergence from such gradients.

## Install
```shell
cd mms-curvature/
python3 -m pip install .  # don't forget the period
``` 

NOTE: the python version DOES NOT contain the time step data in the same array as the gradient or curvature vector as in a tplot variable.  For this reason the *t_master* product is returned.

## Example
```python
import time
import re

import numpy as np
import pytplot

from mms_curvature import DataLoad, mms_Grad, mms_Curvature

start_time =  time.time()
print("Files Loading:")

data = DataLoad(trange=['2017-05-04', '2017-05-05'])
postimes = [pytplot.get_data(n).times for n in data['mec'] if re.compile('mms\d_mec_r_gsm').match(n)]
posvalues = [pytplot.get_data(n).y for n in data['mec'] if re.compile('mms\d_mec_r_gsm').match(n)]
magtimes = [pytplot.get_data(n).times for n in data['fgm'] if re.compile('mms\d_fgm_b_gsm_srvy_l2_bvec').match(n)]
magvalues = [pytplot.get_data(n).y for n in data['fgm'] if re.compile('mms\d_fgm_b_gsm_srvy_l2_bvec').match(n)]

print(f'MMS MEC and FGM data loaded in {time.time()-start_time :.0f} seconds.')

grad_Harvey, bm, bmag, rm, t_master = mms_Grad(postimes, posvalues, magtimes, magvalues)
curve_Harvey = mms_Curvature(grad_Harvey, bm)

np.savetxt("t_master.csv", t_master, delimiter=",")
np.savetxt("curve_Harvey.csv", curve_Harvey, delimiter=",")
np.save("grad_Harvey.npy", grad_Harvey)
```

## References
Equations and methods used can be found at:

- *Analysis Methods for Multi-Spacecraft Data* (Paschmann & Daly, Eds.) Ch.12 'Spatial Gradiants and Volumetric Tensor' by Christopher C. Harvey.  **http://www.issibern.ch/PDF-Files/analysis_methods_1_1a.pdf**
- "Analyses on the geometrical structure of magnetic field in the current sheet based on cluster measurements" (2003) by C. Shen, et al.  **[DOI:10.1029/2002ja009612](https://doi.org/10.1029/2002JA009612)**

## License
Released under Apache 2.0 license (see LICENSE file).  Click **[HERE](https://tldrlegal.com/license/apache-license-2.0-(apache-2.0))** for a summary of what is/isn't allowed.



[![DOI](https://zenodo.org/badge/187900473.svg)](https://zenodo.org/badge/latestdoi/187900473)


