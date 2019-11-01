#!/bin/bash
inp_vid=$1 #"videos/class_04_25_19_halfsec_1080.mp4"
sav_box=$2 #"boxes/class_04_25_19_halfsec_1080.pkl"
sav_vid=$3 #"videos/class_04_25_19_halfsec_1080_out.mp4"
ove_vid=$4 #"videos/class_04_25_19_halfsec_1080_overlay.avi"
con_vid=$5 #"videos/class_04_25_19_halfsec_1080_overlay.mp4"
imdir=$6 #"imdata"
data=$7 #"records.db"
loc=$8 #"TJ200C"
fps=$9 #60
dtime=${10} #"2019-05-12"
inp_mod=${11} #"models/class.h5"
echo "Changing Working Directory To attendance"
cd ..
#python3 detection.py --video vids/me.mp4 --track --save-boxes boxes/test.pkl --save-video vids/me_out.mp4 --imagedir imdata --database records.db --location "TJ202"
source ~/miniconda3/etc/profile.d/conda.sh

echo "Detecting Faces In Video " $inp_vid " taken at " $loc " and taken in " $fps " frames per second"
if [ ${12} == "" ]; then 
	python3 detection.py --video $inp_vid --track --no-display --save-boxes $sav_box --save-video $sav_vid --imagedir $imdir --database $data --location $loc --fps $fps
else
	echo "With Boxes " ${12}
	python3 detection.py --video $inp_vid --track --no-display --save-boxes $sav_box --save-video $sav_vid --boxes ${12} --imagedir $imdir --database $data --location $loc --fps $fps	
fi
echo "Saved Data to " $data " and raw images to " $imdir " and boxes at " $sav_box

echo "Classifying Faces From Database " $data " taken on " $dtime " at " $loc " with model " $inp_mod
conda activate sys
python3 class_train.py --database $data --datetime $dtime --location $loc --load $inp_mod --test 
echo "Saved Classifications To " $data

echo "Leaving Conda Environment"
conda deactivate

echo "Overlaying Video " $inp_vid " taken on " $dtime " at " $loc " in " $fps " frames per second to " $ove_vid
python3 tag.py --database $data --datetime $dtime --location $loc --names --option 9 --video $inp_vid --save-video $ove_vid --fps $fps

echo "Removing Video " $con_vid " To Prevent Confirmation Message"
rm $con_vid

echo "Converting Video " $ove_vid " To " $con_vid
ffmpeg -i $ove_vid $con_vid

echo "Finished"

