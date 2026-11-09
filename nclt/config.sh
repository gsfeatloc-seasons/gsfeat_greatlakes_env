# Settings shared by every NCLT step. The first session is used to train the splat.
SESSIONS="2012-08-04 2012-11-04 2012-02-12"
MAP_SESSION="${SESSIONS%% *}"
NCLT_URL="https://s3.us-east-2.amazonaws.com/nclt.perl.engin.umich.edu"
STRETCH_DIR="data/nclt/stretch_A"
SPLAT_DIR="results/splat/stretch_A_$MAP_SESSION"
RESULTS_DIR="results/gsfeatloc/stretch_A_$MAP_SESSION"
