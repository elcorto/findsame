#!/bin/sh

set -eu

exe=../../bin/findsame

mkdir -p data/empty_dir_1
mkdir -p data/empty_dir_2

$exe -o1 data | jq sort > ref_output_o1.json
$exe -o2 data | jq > ref_output_o2.json
$exe -o3 data | jq > ref_output_o3.json

rm -rf data/empty_dir_1
rm -rf data/empty_dir_2


$exe -l auto -L30 -c3 -o3 data/limit > ref_output_test_auto_limit_L_30

$exe -l auto -L 150 -c2 -v data/limit | grep auto_limit \
    | grep -v 'del leaf fpr' > ref_output_test_auto_limit_debug


