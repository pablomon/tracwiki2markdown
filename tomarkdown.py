import csv
import argparse
import subprocess

######################

# Crea un objeto ArgumentParser
parser = argparse.ArgumentParser(description='Traductor de textos opengnsys')

# Agrega argumentos
parser.add_argument('inputFile', type=str, help='CSV a traducir')
parser.add_argument('outputFile', type=str, help='Destino')
# parser.add_argument('lang', type=str, default='', help='Language root for wikijs')

# Parsea los argumentos de la línea de comandos
args = parser.parse_args()

# lang = args.lang

def translate(text, directory):
    with open("tempin", 'w') as tempfile:
        tempfile.write(text)
    tempfile.close()

    res = ""
    with open("tempout", 'w') as tempfile:
        # res = subprocess.check_output(['python3', 'conversor.py', '--inputFile', 'tempin', '--currentDir', directory, '--lang', lang], text=True)
        res = subprocess.check_output(['python3', 'conversor.py', '--inputFile', 'tempin', '--currentDir', directory], text=True)
    tempfile.close()

    return res

# Abre el archivo CSV en modo lectura
with open(args.inputFile, 'r') as inputcsv:
    # Crea un objeto lector de diccionarios CSV usando el separador ';'
    csvReader = csv.DictReader(inputcsv, delimiter=';')

    # Abre el archivo en modo escritura ('w')
    with open(args.outputFile, 'w') as outputcsv:
        cols = csvReader.fieldnames
        if len(cols) >= 5:
            # Crea un objeto escritor de diccionarios CSV
            csvWriter = csv.DictWriter(outputcsv, fieldnames=[cols[0], cols[1], cols[2], cols[3], cols[4]], delimiter=';')

            # Escribe la fila de encabezados en el archivo de salida
            csvWriter.writeheader()

            # Itera sobre las filas hasta llegar a la fila deseada
            for r, row in enumerate(csvReader, start=1):
                print("Traduciendo fila %d" % r)
                csvWriter.writerow({
                    cols[0]: row[cols[0]], 
                    cols[1]: row[cols[1]],
                    cols[2]: row[cols[2]],
                    cols[3]: row[cols[3]],
                    cols[4]: translate(row[cols[4]], row[cols[0]]),
                    })

        else:
            print("El archivo no tiene las columnas necesarias")
