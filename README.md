# Spark cluster deploy tools for Openstack

This project provides scripts for Apache Spark cluster autodeploy in any Openstack environment with optional useful tools:

* Openstack Swift seamless integration
* Apache Hadoop
* Apache Ignite
* Apache Cassandra
* ElasticSearch
* Jupyter
* NFS share mounts
* Ganglia

Our tools do not need prebuilt images; you can just use vanilla ones. Supported distros are listed at the end of this page.

All the versions of Apache Spark since 1.0 are supported; you are free to choose needed versions of Spark and Hadoop.

Developed in [Institute for System Programming of the Russian Academy of Sciences](http://www.ispras.ru/en/) and distributed with Apache 2.0 license.

You are welcome to contribute.


Installation
============

1. Install ansible version >= 2.2 and < 2.3.0 (it's unsupported yet).

    It looks like Openstack stuff in Ansible will only work with Python 2.7, so if Ansible is already installed for Python 3, you should use virtual environment with Python 2 or be careful with your $PATH (path for Ansible for Python2 should be the first one)

    Old versions of packages can cause problems, in that case `pip --upgrade` could help (e.g. for Ubuntu):

        sudo apt-get install libffi-dev libssl-dev python-dev
        pip install --upgrade pip
        pip install --upgrade six ansible shade

    Also, for some weird reson, six should be installed with `easy_install` instead of `pip` on Mac OS in some cases ([issue on github](https://github.com/major/supernova/issues/55))

    A sample list of all packages and their versions that works can be found in [pip-list.txt](pip-list.txt). Note: it's a result of pip freeze output for virtualenv; formally speaking we depend only on Ansible, six and shade: all the other packages are their dependencies.


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
           [--async] [--yarn] launch <cluster-name>

    replacing <xxx> with values of:

    * `<key-pair-name>` - key pair name
    * `<private-key>` - path to private key file
    * `<n-slaves>` - number of slaves
    * `<instance-type>` - instance flavor that exists in your Openstack environment (e.g. spark.large)
    * `<virtual-network>` - your virtual network name or ID (in Neutron or Nova-networking)
    * `<floating-ip-pool>` - floating IP pool name
    * `<cluster-name>` - name of the cluster (prefix 'surname' is a good practice)
    * `--async` - launch Openstack instances in async way (preferred, but can cause problems on Openstack before Kilo)
    * `--yarn` - Spark-on-YARN deploy mode  (has overhead on memory so do not use it if you don't know why)

    Spark-specific optional arguments:

    * `--spark-version <version>` use specific Spark version. Default is 1.6.2.
    * `--hadoop-version <version>` use specific Hadoop version for Spark. Default is the latest supported in Spark.
    * `--spark-worker-mem-mb <mem>` don't auto-detect spark worker memory and use specified value, can be useful if other
        processes on slave nodes (e.g. python) need more memory, default for 10Gb-20Gb RAM slaves is to leave 2Gb to
        system/other processes; example: `--spark-worker-mem-mb 10240`
    * `--spark-master-instance-type <instance-type>` use another instance flavor for master

    Example:
                ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               launch borisenko-cluster

* To destroy a cluster, run

        ./spark-openstack -k <key-pair-name> -i <private-key> -s <n-slaves> \
           -t <instance-type> -a <os-image-id> --async destroy <cluster-name>

    all parameter values are same as for `launch` command

# Optional goodies

## Select Java version to use on the cluster

By default, OpenJDK is used

If you wish to use Oracle Java, add an optional argument:

     --use-oracle-java

## Enabling Openstack Swift support

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

## Enabling and accessing Jupyter notebook

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

## Manually running Jupyter (e.g after cluster restart)


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

Apache Ignite
=============

You may want to deploy Apache Ignite to the same cluster. To do so you should provide the following
arguments:

    --deploy-ignite

optional arguments:

* `--ignite-memory <prc>` percentage (integer number from 0 to 100) of worker memory to be assigned to Apache Ignite.
    Currently this simply reduces spark executor memory, Apache Ignite memory usage must be manually configured.
* `--ignite-version <ver>` Apache Ignite version to use

Usage example:

    ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               --deploy-ignite --ignite-memory 30\
               launch borisenko-cluster

Ignite configuration is stored in `/opt/ignite/config/default-config.xml`. Note that Spark applications that use
Apache Ignite still need to use `ignite-spark` and `ignite-spring` Spark packages (e.g. for Apache Ignite version 1.7.0
one can run spark shell like this: `spark-shell  --packages org.apache.ignite:ignite-spark:1.7.0,org.apache.ignite:ignite-spring:1.7.0`)

Loading default config can be done as follows:

 ```scala
 import org.apache.ignite.spark._
 import org.apache.ignite.configuration._
 val ic = new IgniteContext(sc, "/opt/ignite/config/default-config.xml")
 ```

## Apache Cassandra

You may want to deploy Apache Cassandra to the cluster. To do so, provide an argument:

    --deploy-cassandra

Optionally, you may specify a version to deploy by providing:

    --cassandra-version <version>

Cassandra 3.11.0 is deployed by default

Usage example:

     ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               --deploy-cassandra\
               launch borisenko-cluster

## ElasticSearch

You may want to deploy ElasticSearch to the cluster. This is done via official ElasticSearch ansible role which is included as a git submodule.

First, init/or update Git submodules:
`git submodule init` or `git submodule update`

Then, you will be able to deploy ElasticSearch by providing:

    --deploy-elastic

Latest ElasticSearch version (5.x) is deployed.

You may want to change ElasticSearch heap size. You can do so by specifying

    --es-heap-size <desized size>

Default heap size is `1g` (1 GB)


Usage example:

    ./spark-openstack -k borisenko -i /home/al/.ssh/id_rsa -s 10 \
               -t spark.large -a 8ac6a0eb-05c6-40a7-aeb7-551cb87986a2 -n abef0ea-4531-41b9-cba1-442ba1245632 -f public \
               --deploy-elastic\
               launch borisenko-cluster

Additional actions
==================

There is support for on-fly setup actions. To use it you should run on existing cluster:

    cd spark-openstack
    ./spark-openstack -k <key-pair-name> -i <private-key> -s <n-slaves> \
       -t <instance-type> -a <os-image-id> -n <virtual-network-id> -f <floating-ip-pool> \
       config <cluster-name> <action>

Supported actions:

* `ganglia` - setups ganglia cluster
* `restart-spark` - restarts Apache Spark
* `restart-cassandra` - restarts Apache Cassandra


## Important notes

* If any of actions fail after all instances are in active state, you can easily rerun the script and it will finish the work quite fast
* If you have only one virtual network in your Openstack project you may not specify it in options, it will be picked up automatically
* You may see output for tasks that are actually weren't done (even errors like '{"failed": true, "msg": "'apt_pkg_pref' is undefined"}'). Do not worry please, the skipped tasks are really skipped and such behaviour is related to [this Ansible issue](https://github.com/ansible/ansible/issues/9034)
* You should use cloud-ready images (e.g for Ubuntu they can be found at https://cloud-images.ubuntu.com/ )
* All unknown arguments are passed to `ansible-playbook`
## Tested configurations

Ansible: 2.0.2 and higher.

Python: 2.7.* (3.x should work as soon as Ansible Openstack modules would be fixed)

Management machine OS: Mac OS X Yosemite, Linux Mint 17, Kubuntu 14.04, Windows+Cygwin

Guest OS:

* Ubuntu 14.04.1-5 (full coverage of all the functionality have been tested; recommended)
* Ubuntu 16.04 (Spark+Hadoop functionality has been tested; other should work also but we didn't check)
* Ubuntu 12.04 (Spark+Hadoop functionality has been tested; other should work also but we didn't check)


* CentOS 6/7 are *unsupported for now* but it should be rather easy to implement, waiting for your pull or feature requests since we don't use it.




## Known issues

* Limited support for security groups in Openstack. Current rules allow all the traffic ingress and egress.
* You may notice a role named jupyterhub - it's senseless to use for now.
* Links to workers and in YARN web-interface are wrong if you don't have DNSaaS in your Openstack (it uses hostnames instead of public IPs)

## TODO Roadmap (you are welcome to contribute)

* Text config file support to avoid specifying lots of cmd parameters
* Openstack security groups full support
* JupyterHUB support for Spark on YARN deploy mode
* More guest OS support
