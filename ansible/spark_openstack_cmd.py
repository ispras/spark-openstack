#!/usr/bin/env python
# -*- coding: utf-8 -*-



from __future__ import print_function
import argparse
import sys
import subprocess
import os
import urllib
from zipfile import ZipFile
from shutil import rmtree
import urlparse


spark_versions = \
    {
        "2.2.0": {"hadoop_versions": ["2.6", "2.7"]},
        "2.1.0": {"hadoop_versions": ["2.3", "2.4", "2.6", "2.7"]},
        "2.0.2": {"hadoop_versions": ["2.3", "2.4", "2.6", "2.7"]},
        "2.0.1": {"hadoop_versions": ["2.3", "2.4", "2.6", "2.7"]},
        "2.0.0": {"hadoop_versions": ["2.3", "2.4", "2.6", "2.7"]},
        "1.6.2": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.6.1": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.6.0": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.5.2": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.5.1": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.5.0": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.4.1": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.4.0": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.3.1": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4", "2.6"]},
        "1.3.0": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4"]},
        "1.2.2": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4"]},
        "1.2.1": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4"]},
        "1.2.0": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4"]},
        "1.1.1": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4"]},
        "1.1.0": {"hadoop_versions": ["1", "cdh4", "2.3", "2.4"]},
        "1.0.2": {"hadoop_versions": ["1", "cdh4"]},
        "1.0.1": {"hadoop_versions": ["1", "cdh4"]},
        "1.0.0": {"hadoop_versions": ["1", "cdh4"]},
    }

toree_versions = \
    {
        "1" : "https://www.apache.org/dist/incubator/toree/0.1.0-incubating/toree-pip/apache-toree-0.1.0.tar.gz",
        "2" : "https://www.apache.org/dist/incubator/toree/0.2.0-incubating/toree-pip/toree-0.2.0.tar.gz",
        "3" : "https://www.apache.org/dist/incubator/toree/0.3.0-incubating/toree-pip/toree-0.3.0.tar.gz"
    }

parser = argparse.ArgumentParser(description='Spark cluster deploy tools for Openstack.',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog='Usage real-life examples:\t\n'
                                        '   ./spark-openstack -k borisenko -i ~/.ssh/id_rsa -s 2 -t spark.large -a 20545e58-59de-4212-a83f-3703b31622cf -n computations-net -f external_network --async launch spark-cluster\n'
                                        '   ./spark-openstack --async destroy spark-cluster\n'
                                        'Look through README.md for more advanced usage examples.\n'
                                        'Apache 2.0, ISP RAS 2016 (http://ispras.ru/en).\n')

parser.add_argument('action', type=str,
                    choices=["launch", "destroy", "get-master", "config"])
parser.add_argument('cluster_name', help="Name for your cluster")
parser.add_argument('option', nargs='?')
parser.add_argument('-k', '--key-pair')
parser.add_argument("-i", "--identity-file")
parser.add_argument("-s", "--slaves", type=int)
parser.add_argument("-n", "--virtual-network", help="Your virtual Openstack network id for cluster. If have only one network, you may not specify it")
parser.add_argument("-f", "--floating-ip-pool", help="Floating IP pool")
parser.add_argument("-t", "--instance-type")
parser.add_argument("-m", "--master-instance-type", help="master instance type, defaults to same as slave instance type")
parser.add_argument("-a", "--image-id")
parser.add_argument("-w", help="ignored")
parser.add_argument("--use-oracle-java", action="store_true", help="Use Oracle Java. If not set, OpenJDK is used")
parser.add_argument("--spark-worker-mem-mb", type=int, help="force worker memory value in megabytes (e.g. 14001)")
parser.add_argument("-j", "--deploy-jupyter", action='store_true', help="Should we deploy jupyter on master node.")
parser.add_argument("-jh", "--deploy-jupyterhub",action='store_true', help="Should we deploy jupyterHub on master node")
parser.add_argument("--spark-version", default="1.6.2", help="Spark version to use")
parser.add_argument("--hadoop-version", help="Hadoop version to use")
parser.add_argument("--boot-from-volume", default=False, help="Should the cluster be based on Cinder volumes. "
                                                              "Use it wisely")
parser.add_argument("--hadoop-user", default="ubuntu", help="User to use/create for cluster members")
parser.add_argument("--ansible-bin", help="path to ansible (and ansible-playbook, default='')")
parser.add_argument("--swift-username", help="Username for Swift object storage. If not specified, swift integration "
                                             "is commented out in core-site.xml. You can also use OS_SWIFT_USERNAME"
                                             "environment variable")
parser.add_argument("--swift-password", help="Username for Swift object storage. If not specified, swift integration "
                                             "is commented out in core-site.xml. You can also use OS_SWIFT_PASSWORD"
                                             "environment variable")
parser.add_argument("--nfs-share", default=[], nargs=2, metavar=("<nfs-path>", "<mount-path>"),
                    help="Should we mount some NFS share(s) on instances",
                    action='append')
parser.add_argument("--extra-jars", action="append", help="Add/replace extra jars to Spark (during launch). Jar file names must be different")

parser.add_argument("--deploy-ignite", action='store_true', help="Should we deploy Apache Ignite.")
parser.add_argument("--ignite-memory", default=50, type=float, help="Percentage of Spark worker memory to be given to Apache Ignite.")
parser.add_argument("--ignite-version", default="1.7.0", help="Apache Ignite version to use.")

parser.add_argument("--yarn", action='store_true', help="Should we deploy using Apache YARN.")
parser.add_argument("--deploy-elastic", action='store_true', help="Should we deploy ElasticSearch")
parser.add_argument("--es-heap-size", default='1g', help="ElasticSearch heap size")

parser.add_argument("--deploy-cassandra", action='store_true', help="Should we deploy Apache Cassandra")
parser.add_argument("--cassandra-version", default="2.2.10", help="Apache Cassandra version to use")
parser.add_argument("--skip-packages", action='store_true',
                    help="Skip package installation (Java, rsync, etc). Image must contain all required packages.")
parser.add_argument("--async", action="store_true",
                    help="Async Openstack operations (may not work with some Openstack environments)")
parser.add_argument("--tags", help="Ansible: run specified tags")
parser.add_argument("--skip-tags", help="Ansible: skip specified tags")


#parser.add_argument("--step", action="store_true", help="Execute play step-by-step")

args, unknown = parser.parse_known_args()
if args.tags is not None:
    unknown.append("--tags")
    unknown.append(args.tags)

if args.skip_tags is not None:
    unknown.append("--skip-tags")
    unknown.append(args.skip_tags)

if args.master_instance_type is None:
    args.master_instance_type = args.instance_type

if "_" in args.cluster_name:
    print("WARNING: '_' symbols in cluster name are not supported, replacing with '-'")
    args.cluster_name = args.cluster_name.replace('_', '-')

ansible_cmd = "ansible"
ansible_playbook_cmd = "ansible-playbook"
if args.ansible_bin is not None:
    ansible_cmd = os.path.join(args.ansible_bin, "ansible")
    ansible_playbook_cmd = os.path.join(args.ansible_bin, "ansible-playbook")


def get_cassandra_connector_jar(spark_version):
    spark_cassandra_connector_url = "http://dl.bintray.com/spark-packages/maven/datastax/spark-cassandra-connector/1.6.8-s_2.10/spark-cassandra-connector-1.6.8-s_2.10.jar" \
        if args.spark_version.startswith("1.6") \
        else "http://dl.bintray.com/spark-packages/maven/datastax/spark-cassandra-connector/2.0.3-s_2.11/spark-cassandra-connector-2.0.3-s_2.11.jar"

    spark_cassandra_connector_filename = "/tmp/" + os.path.basename(urlparse.urlsplit(spark_cassandra_connector_url).path)


    if not os.path.exists(spark_cassandra_connector_filename):
        print("Downloading Spark Cassandra Connector for Spark version {0}".format(spark_version))
        urllib.urlretrieve(spark_cassandra_connector_url,filename=spark_cassandra_connector_filename)

    return spark_cassandra_connector_filename



def get_elastic_jar():
    elastic_hadoop_url = "http://download.elastic.co/hadoop/elasticsearch-hadoop-5.5.0.zip"
    elastic_hadoop_filename = "/tmp/" + os.path.basename(urlparse.urlsplit(elastic_hadoop_url).path)
    elastic_dir = "/tmp/elasticsearch-hadoop/"
    archive_path = "elasticsearch-hadoop-5.5.0/dist/elasticsearch-hadoop-5.5.0.jar"
    elastic_path = os.path.join(elastic_dir, archive_path)
    if not os.path.exists(elastic_path):
        print("Downloading ElasticSearch Hadoop integration")
        urllib.urlretrieve(elastic_hadoop_url, filename=elastic_hadoop_filename)

        with ZipFile(elastic_hadoop_filename) as archive:
            archive.extract(archive_path, path=elastic_dir)
        return elastic_path
    else:
        return elastic_path

def make_extra_vars():
    extra_vars = dict()
    extra_vars["action"] = args.action
    extra_vars["n_slaves"] = args.slaves
    extra_vars["cluster_name"] = args.cluster_name
    extra_vars["os_image"] = args.image_id
    extra_vars["os_key_name"] = args.key_pair
    extra_vars["flavor"] = args.instance_type
    extra_vars["master_flavor"] = args.master_instance_type
    extra_vars["floating_ip_pool"] = args.floating_ip_pool
    extra_vars["virtual_network"] = args.virtual_network
    extra_vars["ansible_user"] = args.hadoop_user
    extra_vars["ansible_ssh_private_key_file"] = args.identity_file

    extra_vars["os_project_name"] = os.getenv('OS_PROJECT_NAME') or os.getenv('OS_TENANT_NAME')
    if not extra_vars["os_project_name"]:
        print("It seems that you h aven't sources your Openstack OPENRC file; quiting")
        exit(-1)

    extra_vars["os_auth_url"] = os.getenv('OS_AUTH_URL')
    if not extra_vars["os_auth_url"]:
        print("It seems that you haven't sources your Openstack OPENRC file; quiting")
        exit(-1)

    extra_vars["hadoop_user"] = args.hadoop_user
    if args.action == 'launch':
        extra_vars["spark_version"] = args.spark_version
        if args.hadoop_version:
            if args.hadoop_version not in spark_versions[args.spark_version]["hadoop_versions"]:
                print("Chosen Spark version doesn't support selected Hadoop version")
                exit(-1)
            extra_vars["hadoop_version"] = args.hadoop_version
        else:
            extra_vars["hadoop_version"] = spark_versions[args.spark_version]["hadoop_versions"][-1]
        print("Deploying Apache Spark %s with Apache Hadoop %s"
              % (extra_vars["spark_version"], extra_vars["hadoop_version"]))
    extra_vars["boot_from_volume"] = args.boot_from_volume

    extra_vars["os_swift_username"] = args.swift_username or os.getenv('OS_SWIFT_USERNAME') or None
    if not extra_vars["os_swift_username"]:
        del extra_vars["os_swift_username"]
    extra_vars["os_swift_password"] = args.swift_password or os.getenv('OS_SWIFT_PASSWORD') or None
    if not extra_vars["os_swift_password"]:
        del extra_vars["os_swift_password"]


    extra_vars["use_oracle_java"] = args.use_oracle_java

    extra_vars["deploy_jupyter"] = args.deploy_jupyter
    if (args.deploy_jupyter):
        extra_vars["toree_version"] = toree_versions[extra_vars["spark_version"][0]]

    extra_vars["deploy_jupyterhub"] = args.deploy_jupyterhub
    extra_vars["nfs_shares"] = [{"nfs_path": l[0], "mount_path": l[1]} for l in  args.nfs_share]

    extra_vars["use_yarn"] = args.yarn

    #ElasticSearch deployment => --extra-args
    extra_vars["deploy_elastic"] = args.deploy_elastic
    extra_vars["es_heap_size"] = args.es_heap_size

    #Cassandra deployment => --extra-args
    extra_vars["deploy_cassandra"] = args.deploy_cassandra
    extra_vars["cassandra_version"] = args.cassandra_version

    extra_vars["skip_packages"] = args.skip_packages

    extra_vars["sync"] = "async" if args.async else "sync"

    if args.extra_jars is None:
        args.extra_jars = []

    extra_jars = list()
    def add_jar(path):
        extra_jars.append({"name": os.path.basename(path), "path": os.path.abspath(path)})
    for jar in args.extra_jars:
        if os.path.isdir(jar):
            for f in os.listdir(jar):
                add_jar(os.path.join(jar, f))
        else:
            add_jar(jar)

    # Obtain Cassandra connector jar if cassandra is deployed
    if args.deploy_cassandra:
        cassandra_jar = get_cassandra_connector_jar(args.spark_version)
        add_jar(cassandra_jar)

    if args.deploy_elastic:
        elastic_jar = get_elastic_jar()
        add_jar(elastic_jar)


    extra_vars["extra_jars"] = extra_jars

    extra_vars["deploy_ignite"] = args.deploy_ignite
    extra_vars["ignite_version"] = args.ignite_version

    return extra_vars


def err(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def parse_host_ip(resp):
    """parse ansible debug output with var=hostvars[inventory_hostname].ansible_ssh_host and return host"""
    parts1 = resp.split("=>")
    if len(parts1) != 2: err("unexpected ansible output")
    parts2 = parts1[1].split(":")
    if len(parts2) != 2: err("unexpected ansible output")
    parts3 = parts2[1].split('"')
    if len(parts3) != 3: err("unexpected ansible output")
    return parts3[1]


def get_master_ip():
    res = subprocess.check_output([ansible_cmd,
                                   "-i", "openstack_inventory.py",
                                   "--extra-vars", repr(make_extra_vars()),
                                   "-m", "debug", "-a", "var=hostvars[inventory_hostname].ansible_ssh_host",
                                   args.cluster_name + "-master"])
    return parse_host_ip(res)

def ssh_output(host, cmd):
    return subprocess.check_output(["ssh", "-q", "-t", "-o", "StrictHostKeyChecking=no",
                                    "-o", "UserKnownHostsFile=/dev/null",
                                    "-i", args.identity_file, "ubuntu@" + host, cmd])

def ssh_first_slave(master_ip, cmd):
    #can't do `head -n1 /opt/spark/conf/slaves` since it's not deployed yet
    return ssh_output(master_ip, "ssh %s-slave-1 '%s'" % (args.cluster_name, cmd.replace("'", "'\\''")))

#FIXME: copied from https://github.com/amplab/spark-ec2/blob/branch-1.5/deploy_templates.py
def get_worker_mem_mb(master_ip):
    if args.spark_worker_mem_mb is not None:
        return args.spark_worker_mem_mb
    mem_command = "cat /proc/meminfo | grep MemTotal | awk '{print $2}'"
    slave_ram_kb = int(ssh_first_slave(master_ip, mem_command))
    slave_ram_mb = slave_ram_kb // 1024
    # Leave some RAM for the OS, Hadoop daemons, and system caches
    if slave_ram_mb > 100*1024:
        slave_ram_mb = slave_ram_mb - 15 * 1024 # Leave 15 GB RAM
    elif slave_ram_mb > 60*1024:
        slave_ram_mb = slave_ram_mb - 10 * 1024 # Leave 10 GB RAM
    elif slave_ram_mb > 40*1024:
        slave_ram_mb = slave_ram_mb - 6 * 1024 # Leave 6 GB RAM
    elif slave_ram_mb > 20*1024:
        slave_ram_mb = slave_ram_mb - 3 * 1024 # Leave 3 GB RAM
    elif slave_ram_mb > 10*1024:
        slave_ram_mb = slave_ram_mb - 2 * 1024 # Leave 2 GB RAM
    else:
        slave_ram_mb = max(512, slave_ram_mb - 1300) # Leave 1.3 GB RAM
    return slave_ram_mb


def get_master_mem(master_ip):
    mem_command = "cat /proc/meminfo | grep MemTotal | awk '{print $2}'"
    master_ram_kb = int(ssh_output(master_ip, mem_command))
    master_ram_mb = master_ram_kb // 1024
    # Leave some RAM for the OS, Hadoop daemons, and system caches
    if master_ram_mb > 100*1024:
        master_ram_mb = master_ram_mb - 15 * 1024 # Leave 15 GB RAM
    elif master_ram_mb > 60*1024:
        master_ram_mb = master_ram_mb - 10 * 1024 # Leave 10 GB RAM
    elif master_ram_mb > 40*1024:
        master_ram_mb = master_ram_mb - 6 * 1024 # Leave 6 GB RAM
    elif master_ram_mb > 20*1024:
        master_ram_mb = master_ram_mb - 3 * 1024 # Leave 3 GB RAM
    elif master_ram_mb > 10*1024:
        master_ram_mb = master_ram_mb - 2 * 1024 # Leave 2 GB RAM
    else:
        master_ram_mb = max(512, master_ram_mb - 1300) # Leave 1.3 GB RAM
    return "%s" % master_ram_mb


def get_slave_cpus(master_ip):
    return int(ssh_first_slave(master_ip, "nproc"))





cmdline = [ansible_playbook_cmd]
cmdline.extend(unknown)

extra_vars = make_extra_vars()

if args.action == "launch":
    cmdline_create = cmdline[:]
    cmdline_create.extend(["create.yml", "--extra-vars", repr(extra_vars)])
    subprocess.call(cmdline_create)

    with open(os.devnull, "w") as devnull:
        subprocess.call(["./openstack_inventory.py", "--refresh", "--list"], stdout=devnull) # refresh openstack cache


    cmdline_initial_setup_status = cmdline[:]
    cmdline_initial_setup_status.extend([ "-i", "openstack_inventory.py", "deploy_ssh.yml", "--extra-vars", repr(extra_vars)])
    initial_setup_status = subprocess.call(cmdline_initial_setup_status)

    if initial_setup_status != 0:
        print("One of your instances didn't come up; please do the following:")
        print("    1. Check your instances states in your Openstack dashboard; if there are any in ERROR state, terminate them")
        print("    2. Rerun the script (no need for destroy; it will continue working skipping the work already done)")
        exit(initial_setup_status)
    master_ip = get_master_ip()
    ssh_first_slave(master_ip, "echo 1")
    if not args.deploy_ignite:
        extra_vars["spark_worker_mem_mb"] = get_worker_mem_mb(master_ip)
        extra_vars["yarn_master_mem_mb"] = get_master_mem(master_ip)
    else:
        worker_mem_mb = get_worker_mem_mb(master_ip)
        ignite_mem_ratio = args.ignite_memory/100.0
        #FIXME: improve rounding
        extra_vars["spark_worker_mem_mb"] = int(worker_mem_mb*(1-ignite_mem_ratio))
        extra_vars["ignite_mem_mb"] = int(worker_mem_mb*ignite_mem_ratio)
        extra_vars["yarn_master_mem_mb"] = get_master_mem(master_ip)

    extra_vars["spark_worker_cores"] = get_slave_cpus(master_ip)
    cmdline_inventory = cmdline[:]
    cmdline_inventory.extend(["-v", "-i", "openstack_inventory.py", "deploy.yml", "--extra-vars", repr(extra_vars)])
    subprocess.call(cmdline_inventory)

    print("Cluster launched successfully; Master IP is %s"%(master_ip))
elif args.action == "destroy":
    res = subprocess.check_output([ansible_cmd,
                                   "-i", "openstack_inventory.py",
                                   "--extra-vars", repr(make_extra_vars()),
                                   "-m", "debug", "-a", "var=groups['%s_slaves']" % args.cluster_name,
                                   args.cluster_name + "-master"])
    extra_vars = make_extra_vars()
    cmdline_create = cmdline[:]
    cmdline_create.extend(["create.yml", "--extra-vars", repr(extra_vars)])
    res = subprocess.call(cmdline_create)
elif args.action == "get-master":
    print(get_master_ip())
elif args.action == "config":
    env = dict(os.environ)
    env['ANSIBLE_ROLES_PATH'] = 'roles'
    extra_vars = make_extra_vars()
    extra_vars['roles_dir'] = '../roles'

    cmdline_inventory = cmdline[:]
    if args.option == 'restart-spark': #Skip installation tasks, run only detect_conf tasks
        cmdline_inventory.extend(("--skip-tags", "spark_install"))

    elif args.option == 'restart-cassandra':
        cmdline_inventory.extend(("--skip-tags", "spark_install,cassandra"))

    cmdline_inventory.extend(["-i", "openstack_inventory.py", "actions/%s.yml" % args.option, "--extra-vars", repr(extra_vars)])
    subprocess.call(cmdline_inventory, env=env)
else:
    err("unknown action: " + args.action)
