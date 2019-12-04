#!/bin/bash

if [ -z "${ZENHOME}" ] ; then
	echo "ZENHOME is not defined"
	exit 1
else
	if [ ! -d "${ZENHOME}" ]; then
		echo "ZENHOME does not exist: ${ZENHOME}"
		exit 1
	fi
fi

tar -C ${ZENHOME} -xzvf prodbin.tar.gz

mkdir -vp ${ZENHOME}/etc/supervisor
mkdir -vp ${ZENHOME}/var/zauth
mkdir -vp ${ZENHOME}/libexec
mkdir -vp ${ZENHOME}/lib/python2.7

if [ ! -h ${ZENHOME}/etc/supervisor/zauth_supervisor.conf ]; then
	ln -vfs ${ZENHOME}/etc/zauth/zauth_supervisor.conf ${ZENHOME}/etc/supervisor/zauth_supervisor.conf
fi

cd ${ZENHOME}
python setup.py develop
rm setup.py VERSION
