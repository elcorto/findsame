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
