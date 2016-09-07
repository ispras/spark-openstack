# Spark cluster deploy tools for Openstack

This project provides scripts for Spark cluster autodeploy in any Openstack environment with optional useful tools:

* Openstack Swift seamless integration
* Jupyter
* NFS share mounts
* Ganglia


Developed in [Institute for System Programming of the Russian Academy of Sciences](http://www.ispras.ru/en/) and
distributed with Apache 2.0 license.

You are welcome to contribute.


Installation
============

1. Install ansible version >= 2.0.2 (2.0.1 has a bug in template engine).

    Looks like openstack stuff in ansible will only work with python 2.7, so if ansible is already installed for python 3, it should be uninstalled first (e.g. `sudo pip3 uninstall ansible`).
    
    Old versions of packages can cause problems, in that case `pip --upgrade` could help (e.g. for ubuntu):

        sudo apt-get install libffi-dev libssl-dev python-dev
        sudo pip2 install --upgrade pip
        sudo pip2 install --upgrade six ansible shade
        
    Also, for some weird reson, six should be installed with `easy_install` instead of `pip` on Mac OS in some cases ([issue on github](https://github.com/major/supernova/issues/55))

    A sample list of package versions that works can be found in [pip-list.txt](pip-list.txt)


Configuration
=============

1. Download (unless already done so) <project-name>-openrc.sh from your Openstack Web UI
    (Project > Compute > Access & Security > API Access > Download OpenStack RC File)
    
    If you don't want to enter password each time and don't care about security, replace
    
        read -sr OS_PASSWORD_INPUT
        export OS_PASSWORD=$OS_PASSWORD_INPUT
        
    with (replace &lt;password&gt; with your password)
     
        export OS_PASSWORD="<password>"
        
    WARNING - it's not secure; do not do that.
    
2. Before running `./spark-openstack` this file must be sourced (once per shell session):

        source /path/to/your/<project>-openrc.sh
        
3. Download/upload key pair.
    You'll need both the name of key pair (Key Pair Name column in  Access & Security > Key Pairs) and prite key file.
    Make sure that only user can read private key file (`chmod og= <key-file-name>`).
    Make sure private key does **not** have a passphrase.
    
Running
=======

* To create a cluster, source your <project>-openrc.sh file and run

        cd spark-openstack
        ./spark-openstack -k <key-pair-name> -i <private-key> -s <n-slaves> \
           -t <instance-type> -a <os-image-id> -n <virtual-network> -f <floating-ip-pool> \
           launch <cluster-name>
        
    replacing <xxx> with values of:
    
    * `<key-pair-name>` - key pair name
    * `<private-key>` - path to private key file
    * `<n-slaves>` - number of slaves
    * `<instance-type>` - instance flavor that exists in your Openstack environment (e.g. spark.large)
    * `<virtual-network>` - your virtual network name or ID (in Neutron or Nova-networking)
    * `<floating-ip-pool>` - floating IP pool name
    * `<cluster-name>` - name of the cluster (prefix 'surname' is a good practice)

    Spark-specific optional arguments:
    
    * `--spark-version <version>` use specific Spark version. Default is 1.6.1.
    * `--hadoop-version <version>` use specific Hadoop version for Spark. Default is the latest supported in Spark.
    * `--spark-worker-mem <mem>` don't auto-detect spark worker memory and use specified value, can be useful if other
        processes on slave nodes (e.g. python) need more memory, default for 10Gb-20Gb RAM slaves is to leave 2Gb to
        system/other processes; example: `--spark-worker-mem 10g`
    * `--spark-master-instance-type <instance-type>` use another instance flavor for master
    
    Example:
    ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               launch borisenko-cluster

* To destroy a cluster, run

        ./spark-openstack -k <key-pair-name> -i <private-key> -s <n-slaves> \
           -t <instance-type> -a <os-image-id> destroy <cluster-name>

    all parameter values are same as for `launch` command

## Optional goodies 

Enabling Openstack Swift support
==========================

You may want to use Openstack Swift object storage as a drop-in addition to your HDFS. To enable it, you should specify:

    * `--swift-username <username>` separate user for using Openstack Swift. If you don't specify it, Swift will be
        unavailable by default.
    * `--swift-password <password>` separate user password for using Openstack Swift. If you don't specify it, Swift 
        will be unavailable by default.
        
Usage example:
    
    ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               --swift-username shared --swift-password password \
               launch borisenko-cluster
        
Hadoop usage:

    hadoop distcp file:///<file> swift://<swift-container-name>.<openstack-project-name>/<path-in-container>
    example: hadoop distcp file:///home/ubuntu/test.txt swift://hadoop.computations/test
    
Spark usage example:

    spark-submit --class <class-name> <path-to-jar> swift://hadoop.computations/test

Warning! This options writes swift-username and swift-password in core-site.xml (in two places) as plain text.
You should use it carefully and it's quite reasonable to use separate user for Swift.

Enabling and accessing Jupyter notebook
==========================

You may want to use Jupyter notebook engine. To enable it you should use optional command line parameter:
    
    --deploy-jupyter True
    
Usage example:

    ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               --deploy-jupyter True \
               launch borisenko-cluster
    
Jupyter notebook should be started automatically after cluster is launched.

Master host IP address can be obtained by running `./spark-openstack get-master <cluster-name>`.
Alternatively, you can look for lines like `"msg": "jupyter install finished on 10.10.17.136 (python_version=3)"` in the console output.

Open `<master-ip>:8888` in a browser. Using two Spark kernels at the same time won't work, so if you want a different Spark kernel shutdown the other one first!
    
Manually running Jupyter (e.g after cluster restart)
========================

Login to master (either get master IP from OpenStack Web UI or run `./spark-openstack get-master <cluster-name>`)

    ssh -i <private-key> -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@<master-ip>
    
Make sure it is not already running (e.g. `killall python`)

Run following command on master:
    
    jupyter notebook --no-browser
    
Then open `<master-ip>:8888` in a browser. Using two Spark kernels at the same time won't work, so if you want a different Spark kernel shutdown the other one first!

Nfs mount
=========

You may want to mount some NFS shares on all the servers in your cluster. To do so you should provide the following
optional arguments:

    --nfs-share <share-path> <where-to-mount>
    
Where `<share-path>` is the address of NFS share (e.g. `1.1.1.1:/share/`) and
`<where-to-mount>` is the path in your cluster machines where the share will be mounted (e.g. `/mnt/share`)
    
Usage example:

    ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               --nfs-share 1.1.1.1:/share/ /mnt/share \
               launch borisenko-cluster


Here's a sample of how to access your NFS share in Spark (Scala):

```scala
val a = sc.textFile("/mnt/nfs_share/test.txt")
a.count
```

```scala
val parquetFile = sqlContext.read.parquet("/mnt/nfs_share/test.parquet")
parquetFile.count
```

Additional actions
==================

There is support for on-fly setup actions. To use it you should run on existing cluster:

    cd spark-openstack
    ./spark-openstack -k <key-pair-name> -i <private-key> -s <n-slaves> \
       -t <instance-type> -a <os-image-id> -n <virtual-network-id> -f <floating-ip-pool> \
       config <cluster-name> <action>
       
Supported actions:

* ganglia - setups ganglia cluster
* restart-spark - restarts spark


## Important notes

* If any of actions fail after all instances are in active state, you can easily rerun the script and it will finish the work quite fast
* If you have only one virtual network in your Openstack project you may not specify it in options, it will be picked up automatically  

## Tested configurations

Ansible: 2.0.2

Python: 2.7.*

Management machine OS: Mac OS X Yosemite, Linux Mint 17, Kubuntu 14.04

## Known issues

* No Openstack security groups support for now. So if your Openstack environment uses it, cluster will not work correctly.
* You may notice a role named jupyterhub - it's senseless to use for now.
* Only Ubuntu 14.04 is supported for now as guest system

## TODO Roadmap (you are welcome to contribute)

* Text config file support to avoid specifying lots of cmd parameters
* Openstack security groups support
* Spark on YARN deploy mode
* JupyterHUB support for Spark on YARN deploy mode
* Async cluster creation/destruction as an option (it works unstable so it's disabled now)
* More guest OS support (now only Ubuntu 14.04 is supported)
