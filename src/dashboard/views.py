from multiprocessing import connection
from django.shortcuts import render, redirect
from django.http import HttpResponse
from dashboard.forms import InputFileForm
from dashboard.functions.functions import handle_uploaded_file
from .models import *
from django.conf import settings
import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from django.contrib import messages
import psycopg2
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required(login_url='/connexion/')
def home(request):
    
    invoices = Invoice.objects.all().count()
    products = Product.objects.all().count()
    countries = Country.objects.all().count()
    earningsfloat = DetailInvoice.objects.annotate(as_float=Cast('totalcost', FloatField())).aggregate(Sum('as_float'))
    try:
        # earningsfloat.int(earningsfloat['as_float__sum'])
        earningsfloat = int(earningsfloat['as_float__sum'])
    except:
        pass
    
    context = {'invoices':invoices,'products':products,'countries':countries, 'earningsfloat':earningsfloat}

    return render(request,"dashboard/home.html", context)

@login_required(login_url='/connexion/')
def import_csv(request):  
    if request.method == 'POST':  
        csvFile = InputFileForm(request.POST, request.FILES)  
        if csvFile.is_valid():  
            handle_uploaded_file(request.FILES['file'])
            analyseData(request)
            messages.success(request, 'CSV importé avec succès!')
            return redirect('analyser')
    
    else:  
        csvFile = InputFileForm()  
        return render(request,"dashboard/import.html",{'form':csvFile})

@login_required(login_url='/connexion/')
def analyseData(request):
        
        #Création variable stockage data
        dataset_dir = 'dashboard/static/upload'

        #Création du chemin du fichier CSV
        csv_file = os.getcwd()+'/'+dataset_dir+'/'+"data.csv"

        #Création du dataframe depuis le fichier CSV
        df = pd.read_csv(csv_file, encoding= 'unicode_escape')

        #Mettre en minuscule les noms de colonnes
        df.columns = [x.lower() for x in df.columns]

        # Comptabiliser les données à supprimer #########################
        nbOriginalData = df.index.size
        nbOriginalData = int(nbOriginalData)

        nbDuplicated = df.duplicated().sum()
        nbDuplicated = int(nbDuplicated)

        nbDuplicatedCol = df.duplicated(['invoiceno','stockcode']).sum()
        nbDuplicatedCol = int(nbDuplicatedCol)

        indexQuantity = df[df['quantity']<0].index.size
        nbQuantity0 = int(indexQuantity)

        indexUnitPrice = df[df['unitprice']<=0].index.size
        nbUnitPrice0 = int(indexUnitPrice)

        indexStockCode = df[df["stockcode"].str.match("^[A-Za-z]")==True].index.size
        nbStartChar = int(indexStockCode)

        dataToDelete = nbDuplicated + nbQuantity0 + nbUnitPrice0 + nbStartChar
        
        # Comptabiliser les données à réparer #############################
        #Mettre en minuscule le nom des pays
        lowerCase = df['country'].size
        lowerCase = int(lowerCase)

        #Tous les champs vide dans la DF (colonne CustomerID, colonne Description)
        nbNull = df.isnull().sum().sum()
        nbNull = int(nbNull)

        dataToRepair = lowerCase + nbNull

        dataOrigin = f"Nombre de lignes de facturations: {nbOriginalData}"
        dataToDelete = f"Nombre de lignes à supprimer: {dataToDelete}"
        dataToRepair = f"Nombre de champs réparable: {dataToRepair}"

        #Après nettoyage######################
        #Total données restantes
        dataFinal = nbOriginalData - (nbDuplicated + nbQuantity0 + nbUnitPrice0 + nbStartChar)

        #Pourcentage de donnée à supprimer
        percDataDelete = ((nbDuplicated + nbQuantity0 + nbUnitPrice0 + nbStartChar)/nbOriginalData)*100
        print(percDataDelete)
        percDataDeleteFloat = round(percDataDelete,2)
        print(type(percDataDelete))

        dataFinal = f"Nombre de lignes de facturations: {dataFinal}"
        percDataDelete = f"Pourcentage de suppression: {round(percDataDelete,2)} %"
        print(type(percDataDelete))

        context = {'dataOrigin':dataOrigin, 
                   'dataToDelete':dataToDelete, 
                   'dataToRepair':dataToRepair,
                   'dataFinal':dataFinal,
                   'percDataDelete':percDataDelete,
                   'percDataDeleteFloat':percDataDeleteFloat}

        return render(request, 'dashboard/import-analyser.html', context )

@login_required(login_url='/connexion/')
def cleanData(self, *args, **options):

    try:
        #Création variable stockage data
        dataset_dir = 'dashboard/static/upload'

        #Création du chemin du fichier CSV
        csv_file = os.getcwd()+'/'+dataset_dir+'/'+"data.csv"

        #Création du dataframe depuis le fichier CSV
        df = pd.read_csv(csv_file, encoding= 'unicode_escape')
        nbOriginalData = df.shape[0]
        print("Nb de lignes de données originel: " + str(nbOriginalData))

        #Mettre en minuscule les noms de colonnes
        df.columns = [x.lower() for x in df.columns]

        #Ajouter une colonne totalcost pour calculer le prix * quantité
        df['totalcost'] = df.unitprice * df.quantity
        
        #Supprimer les lignes doublons
        nbDuplicated = df.duplicated().sum()
        df = df.drop_duplicates()
        print("Nb de lignes de données doublons: " + str(nbDuplicated))

        #Supprimer les doublons invoice/stockcode
        nbDuplicatedCol = df.duplicated(['invoiceno','stockcode']).sum()
        df = df.drop_duplicates(['invoiceno','stockcode'])
        print("Nb de lignes de données doublons invoice/stockcode: " + str(nbDuplicatedCol))

        #Supprimer les lignes quantity <=0
        indexQuantity = df[df['quantity']<0].index
        nbQuantity0 = indexQuantity.value_counts()
        df.drop(indexQuantity,inplace=True)
        print("Nb de lignes de données quantity <= 0: " + str(nbQuantity0))

        #Supprimer les lignes unitprice = 0
        indexUnitPrice = df[df['unitprice']<=0].index
        nbUnitPrice0 = indexUnitPrice.value_counts()
        df.drop(indexUnitPrice,inplace=True)
        print("Nb de lignes de données unitprice = 0: " + str(nbUnitPrice0))

        #Supprimer les lignes stockcode qui commence par une chaîne de caractère
        indexStockCode = df[df["stockcode"].str.match("^[A-Za-z]")==True].index
        nbStartChar = indexStockCode.value_counts()
        df.drop(indexStockCode,inplace=True)
        nbFinalData = df.shape[0]
        print("Nb de lignes de données stockcode commencant par une lettre: " + str(nbStartChar))

        # Mettre en Minuscule les lignes country EIRE -> Eire
        df['country'] = df['country'].str.title()
        # print(df['country'].unique())

        #Mettre les lignes avec country NULL ou Numérique en "unspecified"
        #si les autres colonnes ont un intérêt
        df.replace('NaN',np.nan)
        nbCountryNan = df['country'].isnull().sum()
        df['country'].fillna(value='Unspecified')
        print("Nb de lignes de données country vide: " + str(nbCountryNan))
        df['description'].fillna(value='Description du produit à intégrer')

        #Afficher le % de suppression et si <5% dire "envisageable"
        nbDeleteData = nbOriginalData - nbFinalData
        percFinalData = 100-((nbDeleteData*100)/nbOriginalData)
        print("Nb de lignes de données nettoyées: " + str(nbDeleteData))
        print("Pourcentage de données final: " + str(round(percFinalData,2)) + "%")

        user = settings.DATABASES['default']['USER']
        password = settings.DATABASES['default']['PASSWORD']
        database_name = settings.DATABASES['default']['NAME']

        database_url = 'postgresql://{user}:{password}@localhost:5432/{database_name}'.format(user=user,password=password,database_name=database_name)
        engine = create_engine(database_url, echo=False)

        #Transfert de la Dataframe dans une table temporaire de la BDD
        df.to_sql(Datatransfert._meta.db_table, if_exists='replace', con=engine, index=False)
        
        #Requête pour envoi data dans les différentes tables de la BDD
        sql = '''

        ALTER TABLE dashboard_invoice
            ALTER COLUMN invoicedate TYPE text;

        SET CONSTRAINTS ALL IMMEDIATE;

        INSERT INTO dashboard_country(country)
            SELECT country
            FROM dashboard_datatransfert
            ON CONFLICT(country)
            DO NOTHING;

        INSERT INTO dashboard_product(stockcode,description)
            SELECT stockcode,description
            FROM dashboard_datatransfert
            ON CONFLICT(stockcode)
            DO NOTHING;
        
        INSERT INTO dashboard_invoice(invoiceno,invoicedate,customerid,country)
            SELECT invoiceno,invoicedate,customerid,country
            FROM dashboard_datatransfert
            ON CONFLICT(invoiceno)
            DO NOTHING;

        INSERT INTO dashboard_detailinvoice(invoiceno,stockcode,unitprice,quantity,totalcost)
            SELECT invoiceno,stockcode,unitprice,quantity,totalcost
            FROM dashboard_datatransfert
            ON CONFLICT
            DO NOTHING;

        UPDATE dashboard_country SET zone='Earth';

        DELETE FROM dashboard_datatransfert;

        ALTER TABLE dashboard_invoice
            ALTER COLUMN invoicedate TYPE date
            USING invoicedate::date;

        '''

        #Executer la requête pour envoi dans la BDD Postgre
        engine.execute(sql)

        #Supprimer le fichier CSV importé
        for folder, subfolders, files in os.walk('dashboard/static/upload'): 
            for file in files: 
                # Vérifier si le fichir fini en .csv 
                if file.endswith('.csv'): 
                    path = os.path.join(folder, file)      
                    print('deleted : ', path )
                    # supprimer le csv 
                    os.remove(path)
    except FileNotFoundError as e:
        print("Veuillez importer un fichier CSV d'abord")
    
    messages.success(self, 'CSV nettoyé et enregistré dans la base de donnée!')
    return redirect("import")

@login_required(login_url='/connexion/')
def deleteData(self):

    detailInvoices = DetailInvoice.objects.all().delete()
    invoices = Invoice.objects.all().delete()
    products = Product.objects.all().delete()
    countries = Country.objects.all().delete()

    # context = {'invoices':invoices, 'detailInvoices':detailInvoices, 'products':products, 'countries':countries}

    return redirect('home')

@login_required(login_url='/connexion/')
def sellByCountryTop(request):

    sql = '''SELECT dashboard_invoice.country, count(*) 
                FROM dashboard_detailinvoice 
                INNER JOIN dashboard_invoice ON dashboard_detailinvoice.invoiceno = dashboard_invoice.invoiceno 
                GROUP BY dashboard_invoice.country
                ORDER BY count DESC 
                LIMIT 10'''

    res = Country.objects.raw(sql)
    top = 'all years'

    context = {'data': res, 'top':top}

    return render(request, "dashboard/graphique-region.html", context)

@login_required(login_url='/connexion/')
def sellByCountryTop2010(request):
    
    sql = '''SELECT EXTRACT(YEAR FROM i.invoicedate), i.country, count(*) 
                FROM dashboard_invoice as i
                INNER JOIN dashboard_detailinvoice as di
                ON i.invoiceno = di.invoiceno
                WHERE EXTRACT(YEAR FROM i.invoicedate) = 2010
                GROUP BY EXTRACT(YEAR FROM i.invoicedate), i.country
                ORDER BY count DESC
                LIMIT 10'''
    
    res = Country.objects.raw(sql)
    top = '2010'

    context = {'data': res, 'top':top}

    return render(request, "dashboard/graphique-region.html", context)

@login_required(login_url='/connexion/')
def sellByCountryTop2011(request):
    
    sql = '''SELECT EXTRACT(YEAR FROM i.invoicedate), i.country, count(*) 
                FROM dashboard_invoice as i
                INNER JOIN dashboard_detailinvoice as di
                ON i.invoiceno = di.invoiceno
                WHERE EXTRACT(YEAR FROM i.invoicedate) = 2011
                GROUP BY EXTRACT(YEAR FROM i.invoicedate), i.country
                ORDER BY count DESC
                LIMIT 10'''
    
    res = Country.objects.raw(sql)
    top = '2011'

    context = {'data': res, 'top':top}

    return render(request, "dashboard/graphique-region.html", context)

@login_required(login_url='/connexion/')
def sellByCountryFlop(request):

    sql = '''SELECT dashboard_invoice.country, count(*) 
                FROM dashboard_detailinvoice 
                INNER JOIN dashboard_invoice ON dashboard_detailinvoice.invoiceno = dashboard_invoice.invoiceno 
                GROUP BY dashboard_invoice.country
                ORDER BY count ASC 
                LIMIT 10'''

    res = Country.objects.raw(sql)

    return render(request, "dashboard/graphique-region.html", {'data': res})

@login_required(login_url='/connexion/')
def sellByCountryFlop2010(request):
    
    sql = '''SELECT EXTRACT(YEAR FROM i.invoicedate), i.country, count(*) 
                FROM dashboard_invoice as i
                INNER JOIN dashboard_detailinvoice as di
                ON i.invoiceno = di.invoiceno
                WHERE EXTRACT(YEAR FROM i.invoicedate) = 2010
                GROUP BY EXTRACT(YEAR FROM i.invoicedate), i.country
                ORDER BY count ASC
                LIMIT 10'''
    
    res = Country.objects.raw(sql)

    return render(request, "dashboard/graphique-region.html", {'data': res})

@login_required(login_url='/connexion/')
def sellByCountryFlop2011(request):

    sql = '''SELECT EXTRACT(YEAR FROM i.invoicedate), i.country, count(*) 
                FROM dashboard_invoice as i
                INNER JOIN dashboard_detailinvoice as di
                ON i.invoiceno = di.invoiceno
                WHERE EXTRACT(YEAR FROM i.invoicedate) = 2011
                GROUP BY EXTRACT(YEAR FROM i.invoicedate), i.country
                ORDER BY count ASC
                LIMIT 10'''
    
    res = Country.objects.raw(sql)

    return render(request, "dashboard/graphique-region.html", {'data': res})

@login_required(login_url='/connexion/')
def sellByProductTop(request):

    sql=('''SELECT dashboard_detailinvoice.stockcode, count(*) 
                FROM dashboard_detailinvoice 
                INNER JOIN dashboard_invoice ON dashboard_detailinvoice.invoiceno = dashboard_invoice.invoiceno 
                GROUP BY dashboard_detailinvoice.stockcode
                ORDER BY count DESC 
                LIMIT 10''')

    res = Product.objects.raw(sql)
    top = 'all years'

    context = {'data': res, 'top':top}

    return render(request, "dashboard/graphique-produit.html", context)

@login_required(login_url='/connexion/')
def sellByProductTop2010(request):

    sql=('''SELECT EXTRACT(YEAR FROM i.invoicedate), di.stockcode, count(*) 
			FROM dashboard_invoice as i
			INNER JOIN dashboard_detailinvoice as di
			ON i.invoiceno = di.invoiceno
			WHERE EXTRACT(YEAR FROM i.invoicedate) = 2010
			GROUP BY EXTRACT(YEAR FROM i.invoicedate), di.stockcode
			ORDER BY count DESC
			LIMIT 10''')

    res = Product.objects.raw(sql)
    top = '2010'

    context = {'data': res, 'top':top}

    return render(request, "dashboard/graphique-produit.html", context)

@login_required(login_url='/connexion/')
def sellByProductTop2011(request):

    sql=('''SELECT EXTRACT(YEAR FROM i.invoicedate), di.stockcode, count(*) 
			FROM dashboard_invoice as i
			INNER JOIN dashboard_detailinvoice as di
			ON i.invoiceno = di.invoiceno
			WHERE EXTRACT(YEAR FROM i.invoicedate) = 2011
			GROUP BY EXTRACT(YEAR FROM i.invoicedate), di.stockcode
			ORDER BY count DESC
			LIMIT 10''')

    res = Product.objects.raw(sql)
    top = '2011'

    context = {'data': res, 'top':top}

    return render(request, "dashboard/graphique-produit.html", context)

@login_required(login_url='/connexion/')
def sellByProductFlop(request):

    sql=('''SELECT dashboard_detailinvoice.stockcode, count(*) 
                FROM dashboard_detailinvoice 
                INNER JOIN dashboard_invoice ON dashboard_detailinvoice.invoiceno = dashboard_invoice.invoiceno 
                GROUP BY dashboard_detailinvoice.stockcode
                ORDER BY count ASC 
                LIMIT 10''')

    res = Product.objects.raw(sql)

    return render(request, "dashboard/graphique-produit.html", {'data': res})

@login_required(login_url='/connexion/')
def sellByProductFlop2010(request):

    sql=('''SELECT EXTRACT(YEAR FROM i.invoicedate), di.stockcode, count(*) 
			FROM dashboard_invoice as i
			INNER JOIN dashboard_detailinvoice as di
			ON i.invoiceno = di.invoiceno
			WHERE EXTRACT(YEAR FROM i.invoicedate) = 2010
			GROUP BY EXTRACT(YEAR FROM i.invoicedate), di.stockcode
			ORDER BY count ASC
			LIMIT 10''')

    res = Product.objects.raw(sql)

    return render(request, "dashboard/graphique-produit.html", {'data': res})

@login_required(login_url='/connexion/')
def sellByProductFlop2011(request):

    sql=('''SELECT EXTRACT(YEAR FROM i.invoicedate), di.stockcode, count(*) 
			FROM dashboard_invoice as i
			INNER JOIN dashboard_detailinvoice as di
			ON i.invoiceno = di.invoiceno
			WHERE EXTRACT(YEAR FROM i.invoicedate) = 2011
			GROUP BY EXTRACT(YEAR FROM i.invoicedate), di.stockcode
			ORDER BY count ASC
			LIMIT 10''')

    res = Product.objects.raw(sql)

    return render(request, "dashboard/graphique-produit.html", {'data': res})

@login_required(login_url='/connexion/')
def sellByCountryProduct(request):

    sql=('''SELECT dashboard_detailinvoice.stockcode, count(*) 
                FROM dashboard_detailinvoice 
                INNER JOIN dashboard_invoice ON dashboard_detailinvoice.invoiceno = dashboard_invoice.invoiceno 
                GROUP BY dashboard_detailinvoice.stockcode
                ORDER BY count ASC 
                LIMIT 10''')

    res = Product.objects.raw(sql)

    return render(request, "dashboard/graphique-region-produit.html", {'data': res})

def dictfetchall(cursor):
    desc = cursor.description
    return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
    ]

@login_required(login_url='/connexion/')
def sellByMonth(request):

    #establishing the connection
    conn = psycopg2.connect(
        database="DB_Analysis_Business_Intelligence", user='moni', password='moni', host='127.0.0.1', port= '5432'
    )

    #Setting auto commit false
    conn.autocommit = True

    #Creating a cursor object using the cursor() method
    cursor = conn.cursor()
    cursor.execute('''SELECT EXTRACT(MONTH FROM i.invoicedate) as month, count(*) 
                        FROM dashboard_invoice as i
                        INNER JOIN dashboard_detailinvoice as di
                        ON i.invoiceno = di.invoiceno
                        GROUP BY EXTRACT(MONTH FROM i.invoicedate)
                        ORDER BY month asc''')

    r = dictfetchall(cursor)

    cursor.execute('''SELECT EXTRACT(MONTH FROM i.invoicedate) as month, ROUND(sum(di.totalcost)) as cout
                        FROM dashboard_invoice as i
                        INNER JOIN dashboard_detailinvoice as di
                        ON i.invoiceno = di.invoiceno
                        GROUP BY EXTRACT(MONTH FROM i.invoicedate)
                        ORDER BY month asc''')

    r2 = dictfetchall(cursor)

    cursor.close()

    context = {'data1': r, 'data2': r2}

    return render(request, "dashboard/graphique-vente-mensuelle.html", context)





# Fonction à utiliser avec la méthode ci-dessous
# def dictfetchall(cursor):
#     desc = cursor.description
#     return [
#             dict(zip([col[0] for col in desc], row))
#             for row in cursor.fetchall()
#     ]

# Fonction avec une autre méthode
# def sell_by_country(request):

#     cursor = connection.cursor()
#     cursor.execute('''SELECT dashboard_invoice.country, count(*) 
#                             FROM dashboard_detailinvoice 
#                             INNER JOIN dashboard_invoice ON dashboard_detailinvoice.invoiceno = dashboard_invoice.invoiceno 
#                             GROUP BY dashboard_invoice.country
#                             ORDER BY count DESC 
#                             LIMIT 10''')

#     r = dictfetchall(cursor)

#     cursor.close()
#     return render(request, "dashboard/graphique-region.html", {'data': res})
