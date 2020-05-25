#!/bin/sh

dr=data/limit

yes a | head -n 2000 | tr -d '\n' > $dr/file_2000_a

yes a | head -n 200 | tr -d '\n' > $dr/file_200_a_200_b_1600_c
yes a | head -n 200 | tr -d '\n' > $dr/file_200_a_200_b_1600_d

yes a | head -n 200 | tr -d '\n' > $dr/other/file_200_a
yes a | head -n 200 | tr -d '\n' > $dr/other/file_200_a_200_b


yes b | head -n 200 | tr -d '\n' >> $dr/file_200_a_200_b_1600_c
yes b | head -n 200 | tr -d '\n' >> $dr/file_200_a_200_b_1600_d

yes b | head -n 200 | tr -d '\n' >> $dr/other/file_200_a_200_b


yes c | head -n 1600 | tr -d '\n' >> $dr/file_200_a_200_b_1600_c

yes d | head -n 1600 | tr -d '\n' >> $dr/file_200_a_200_b_1600_d
