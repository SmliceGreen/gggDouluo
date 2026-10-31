# This book uses Unicode fonts and requires XeLaTeX.
$pdf_mode = 5;
$xelatex = 'xelatex -no-shell-escape -halt-on-error %O %S';
# Some editors explicitly pass -pdf; keep that route on XeLaTeX too.
$pdflatex = $xelatex;
