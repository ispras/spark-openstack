#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import argparse
import sys
import subprocess
import os

spark_versions = \
    {
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

parser = argparse.ArgumentParser(description='Spark cluster deploy tools for Openstack.',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog='Usage example:\t'
                                        './spark-openstack -k key_name -i ~/.ssh/id_rsa -s 10 -t spark.large -a 20545e58-59de-4212-a83f-3703b31622cf -f public_pool launch spark-cluster'
                                        './spark-openstack -k key_name -i ~/.ssh/id_rsa -s 10 -t spark.large -a 20545e58-59de-4212-a83f-3703b31622cf -f public_pool  destroy spark-cluster'
                                        'Look through README.md for more advanced usage examples.'
                                        'Apache 2.0, ISP RAS 2016.')

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
parser.add_argument("--spark-worker-mem", help="force worker memory value (e.g. 14001m)")
parser.add_argument("-j", "--deploy-jupyter", default=True, help="Should we deploy jupyter on master node.")
parser.add_argument("--spark-version", default="1.6.1", help="Spark version to use")
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
parser.add_argument("--nfs-share", default=False, help="Should we mount some NFS share on instances")
parser.add_argument("--nfs-share-path", help="Path to NFS share")
parser.add_argument("--nfs-share-mnt", help="Where to mount NFS share")

args = parser.parse_args()
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


def make_extra_vars():
    extra_vars = dict()
    extra_vars["instance_state"] = "present"
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
        print("It seems that you haven't sources your Openstack OPENRC file; quiting")
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

    extra_vars["deploy_jupyter"] = args.deploy_jupyter
    extra_vars["nfs_share"] = args.nfs_share
    extra_vars["nfs_share_path"] = args.nfs_share_path
    extra_vars["nfs_share_mnt"] = args.nfs_share_mnt

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
def get_worker_mem(master_ip):
    if args.spark_worker_mem is not None:
        return args.spark_worker_mem
    mem_command = "cat /proc/meminfo | grep MemTotal | awk '{print $2}'"
    slave_ram_kb = int(ssh_first_slave(master_ip, mem_command))
    slave_ram_mb = slave_ram_kb / 1024
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
    return "%sm" % slave_ram_mb

def get_slave_cpus(master_ip):
    return int(ssh_first_slave(master_ip, "nproc"))

if args.action == "launch":
    subprocess.call([ansible_playbook_cmd, "create.yml", "--extra-vars", repr(make_extra_vars())])
    extra_vars = make_extra_vars()
    subprocess.call(["./openstack_inventory.py", "--refresh", "--list"]) # refresh openstack cache
    subprocess.call([ansible_playbook_cmd, "-i", "openstack_inventory.py", "deploy_ssh.yml", "--extra-vars", repr(extra_vars)])
    master_ip = get_master_ip()
    #get rid of 'Warning: Permanently added ...' stuff
    ssh_first_slave(master_ip, "echo 1")
    extra_vars["spark_worker_mem"] = get_worker_mem(master_ip)
    extra_vars["spark_worker_cores"] = get_slave_cpus(master_ip)
    #TODO: check that instances were actually created, otherwise don't deploy and return with error msg
    subprocess.call([ansible_playbook_cmd, "-i", "openstack_inventory.py", "deploy.yml", "--extra-vars", repr(extra_vars)])
elif args.action == "destroy":
    res = subprocess.check_output([ansible_cmd,
                                   "-i", "openstack_inventory.py",
                                   "--extra-vars", repr(make_extra_vars()),
                                   "-m", "debug", "-a", "var=groups['%s_slaves']" % args.cluster_name,
                                   args.cluster_name + "-master"])
    nslaves = len(res.strip().split("\n")) - 4
    print("FIXME: setting slaves = " + str(nslaves))
    args.slaves = nslaves
    extra_vars = make_extra_vars()
    extra_vars["instance_state"] = "absent"
    res = subprocess.call([ansible_playbook_cmd, "create.yml", "--extra-vars", repr(extra_vars)])
elif args.action == "get-master":
    print(get_master_ip())
elif args.action == "config":
    env = dict(os.environ)
    env['ANSIBLE_ROLES_PATH'] = 'roles'
    extra_vars = make_extra_vars()
    extra_vars['roles_dir'] = '../roles'
    subprocess.call([ansible_playbook_cmd, "-i", "openstack_inventory.py", "actions/%s.yml" % args.option, "--extra-vars", repr(extra_vars)], env=env)
else:
    err("unknown action: " + args.action)
