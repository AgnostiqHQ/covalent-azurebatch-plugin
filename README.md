&nbsp;

<div align="center">

<img src="assets/azure_batch_readme_banner.svg" width=150%>

</div>

## Covalent Azure Batch Plugin

Covalent is a Pythonic workflow tool used to execute tasks on advanced computing hardware. This executor plugin interfaces Covalent with [Microsoft Azure Batch](https://azure.microsoft.com/en-us/products/batch/#overview).

## 1. Installation

To use this plugin with Covalent, install it using `pip`:

```sh
pip install covalent-azurebatch-plugin
```

## 2. Usage Example

This is an example of how a workflow can be constructed to use the Azure Batch executor. In the example, we train a Support Vector Machine (SVM) and use an instance of the executor to execute the `train_svm` electron. Note that we also require [DepsPip](https://covalent.readthedocs.io/en/latest/concepts/concepts.html#depspip) which will be required to execute the electrons.

```python
from numpy.random import permutation
from sklearn import svm, datasets
import covalent as ct

from covalent.executor import AzureBatchExecutor

deps_pip = ct.DepsPip(
    packages=["numpy==1.22.4", "scikit-learn==1.1.2"]
)

executor = AzureBatchExecutor(
    tenant_id="tenant-id",
    client_id="client-id",
    client_secret="client-secret",
    batch_account_url="https://covalent.eastus.batch.azure.com",
    batch_account_domain="batch.core.windows.net",
    storage_account_name="covalentbatch",
    storage_account_domain="blob.core.windows.net",
    base_image_uri="covalent.azurecr.io/covalent-executor-base:latest",
    pool_id="covalent-pool",
    retries=3,
    time_limit=300,
    cache_dir="/tmp/covalent",
    poll_freq=10
)


# Use executor plugin to train our SVM model
@ct.electron(
    executor=executor,
    deps_pip=deps_pip
)
def train_svm(data, C, gamma):
    X, y = data
    clf = svm.SVC(C=C, gamma=gamma)
    clf.fit(X[90:], y[90:])
    return clf

@ct.electron
def load_data():
    iris = datasets.load_iris()
    perm = permutation(iris.target.size)
    iris.data = iris.data[perm]
    iris.target = iris.target[perm]
    return iris.data, iris.target

@ct.electron
def score_svm(data, clf):
    X_test, y_test = data
    return clf.score(
    	X_test[:90],y_test[:90]
    )

@ct.lattice
def run_experiment(C=1.0, gamma=0.7):
    data = load_data()
    clf = train_svm(
    	data=data,
	    C=C,
	    gamma=gamma
    )
    score = score_svm(
    	data=data,
	    clf=clf
    )
    return score

# Dispatch the workflow.
dispatch_id = ct.dispatch(run_experiment)(
        C=1.0,
        gamma=0.7
)

# Wait for our result and get result value
result = ct.get_result(dispatch_id, wait=True).result

print(result)
```

During the execution of the workflow, one can navigate to the UI to see the status of the workflow. Once completed, the above script should also output a value with the score of our model.

```sh
0.8666666666666667
```

In order for the above workflow to run successfully, one has to provision the required cloud resources as mentioned in the section [Required Microsoft Azure Batch Resources](#-required-microsoft-azure-batch-resources).

## 3. Configuration

There are many configuration options that can be passed in to the class `ct.executor.AzureBatchExecutor` or by modifying the [covalent config file](https://covalent.readthedocs.io/en/latest/how_to/config/customization.html) under the section `[executors.azurebatch]`.

For more information about all of the possible configuration values visit our [read the docs (RTD) guide](https://covalent.readthedocs.io/en/latest/api/executors/azurebatch.html#overview-of-configuration) for this plugin.

## 4. Required Microsoft Azure Resources

In order to run your workflows with covalent there are a few notable Microsoft Azure resources that need to be provisioned first.

The required Azure resources are:

    1. Batch account

    2. Storage account

    3. Resource group

    4. Container registry (custom images only)

    5. Pool of compute nodes

For more information regarding which cloud resources need to be provisioned visit our [read the docs (RTD) guide](https://covalent.readthedocs.io/en/latest/api/executors/azurebatch.html#required-cloud-resources) for this plugin.

## Getting Started with Covalent

For more information on how to get started with Covalent, check out the project [homepage](https://github.com/AgnostiqHQ/covalent) and the official [documentation](https://covalent.readthedocs.io/en/latest/).

## Release Notes

Release notes are available in the [Changelog](https://github.com/AgnostiqHQ/covalent-azurebatch-plugin/blob/main/CHANGELOG.md).

## Citation

Please use the following citation in any publications:

> W. J. Cunningham, S. K. Radha, F. Hasan, J. Kanem, S. W. Neagle, and S. Sanand.
> _Covalent._ Zenodo, 2022. https://doi.org/10.5281/zenodo.5903364

## License

Covalent is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/AgnostiqHQ/covalent-azurebatch-plugin/blob/main/LICENSE) file or contact the [support team](mailto:support@agnostiq.ai) for more details.
