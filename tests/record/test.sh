#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

bindir=$(dirname "$0")
cd "$bindir"

damon_debugfs="/sys/kernel/debug/damon"
damo="../../damo"

if ! sudo "$damo" record "sleep 3"
then
	echo "FAIL record-sleep-3: command failed"
	exit 1
fi

if ! "$damo" validate
then
	echo "FAIL record-validate-sleep-3"
	exit 1
fi

exit 0
