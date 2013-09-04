#!/bin/bash
if [ $1 ]; then
	echo "Parseando el archivo $1.json"
	./parser.py -i $1.jg -o $1.json

	echo "Determinando branches"
	branches=($(./draw.py -i $1.json -t))
	files=""

	dir=$(dirname $1)

	echo "Los branches son $branches"
	if [ "$branches" ]; then
		for branch in "${branches[@]}"
		do
			echo "Procesando branch $branch"
			./draw.py -i $1.json -o $branch.dot -r $branch
			unflatten -f -l 5 $branch.dot -o $branch_unflatten.dot
			dot -Tpdf $branch_unflatten.dot -o $branch.pdf
			files=$files" $branch.pdf"
		done
		pdftk $files cat output $dir/diagrama.pdf
	else
		echo "No hay branches que procesar, al menos se debe tener un branch principal"
		exit 1
	fi
else
	echo "Falta especificar el [archivo], ubicado en [archivo].jg"
fi
