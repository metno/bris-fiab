date=20250305
hour=00
dir=mosaic
res=0_25deg
#what=wind10m
what=temperature2m
era_file=$dir/ifs_${date}T${hour}.nc
lam_file=$dir/malawi_${date}T${hour}.nc

ofile=movie_${what}_${date}T${hour}_${res}.gif
mkdir -p $dir/images
rm -f "${dir}/images/${what}_${date}T${hour}_${res}_*.png"
for i in `seq -w 00 41`; do
  if [ -f "$dir/images/${what}_${date}T${hour}_${res}_${i}.png" ]; then
    echo "File $dir/images/${what}_${date}T${hour}_${res}_${i}.png exists, skipping"
    continue
  fi
  echo "Creating $dir/images/${what}_${date}T${hour}_${res}_${i}.png"
  python3 create_singlemap.py $era_file $lam_file -lt $i -o "$dir/images/${what}_${date}T${hour}_${res}_${i}.png";
done

convert -delay 80 "${dir}/images/${what}_${date}T${hour}_${res}_00.png" "${dir}/images/${what}_${date}T${hour}_${res}_*.png" $ofile
