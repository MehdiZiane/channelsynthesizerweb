import shutil
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadFilesForm
from .models import UploadedPDF, UploadedExcel, ProcessingBatch
from .processing import process_uploaded_pdfs
import os
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.contrib.auth.decorators import login_required
import uuid
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token


@login_required
def upload_files(request):
    if request.method == 'POST':
        form = UploadFilesForm(request.POST, request.FILES)
        if form.is_valid():
            # Récupérer la valeur de la case à cocher
            include_base_offers = form.cleaned_data.get('include_base_offers', False)

            # Créer un nouveau batch de traitement
            batch = ProcessingBatch.objects.create()

            pdf_files = request.FILES.getlist('pdf_files')
            existing_pdf_files = form.cleaned_data.get('existing_pdf_files')
            excel_file = request.FILES.get('excel_file')
            existing_excel_file = form.cleaned_data.get('existing_excel_file')

            pdf_instances = []

            # Enregistrer les nouveaux fichiers PDF uploadés
            for pdf_file in pdf_files:
                pdf_instance = UploadedPDF(file=pdf_file, batch=batch)
                pdf_instance.save()
                pdf_instances.append(pdf_instance)

            # Ajouter les fichiers PDF existants au batch
            if existing_pdf_files:
                for pdf_instance in existing_pdf_files:
                    pdf_instance.batch = batch
                    pdf_instance.save()
                    pdf_instances.append(pdf_instance)

            # Gérer le fichier Excel
            if excel_file:
                # Enregistrer le nouveau fichier Excel
                excel_instance = UploadedExcel(file=excel_file)
                excel_instance.save()
                # Associer le fichier Excel au batch
                batch.excel_file = excel_instance
                batch.save()
                excel_file_path = excel_instance.file.path
            elif existing_excel_file:
                # Utiliser le fichier Excel existant
                batch.excel_file = existing_excel_file
                batch.save()
                excel_file_path = existing_excel_file.file.path
            else:
                # Cela ne devrait pas arriver en raison de la validation du formulaire
                raise ValueError('Aucun fichier Excel fourni.')

            # Traiter les fichiers
            process_uploaded_pdfs(pdf_instances, excel_file_path, include_base_offers)

            return redirect('download_report')
    else:
        form = UploadFilesForm()
    return render(request, 'pdf_processing/upload_files.html', {'form': form})


def handle_excel_upload(excel_file, batch_id):
    excel_dir = os.path.join(settings.MEDIA_ROOT, 'excel', str(batch_id))
    os.makedirs(excel_dir, exist_ok=True)
    excel_file_path = os.path.join(excel_dir, excel_file.name)
    with open(excel_file_path, 'wb+') as destination:
        for chunk in excel_file.chunks():
            destination.write(chunk)
    return excel_file_path


def download_report(request):
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    report_file = os.path.join(reports_dir, 'consolidated_report.xlsx')
    if os.path.exists(report_file):
        with open(report_file, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(report_file)
            return response
    else:
        return HttpResponseNotFound("The report is not available.")

def processing_page(request):
    # Start processing
    # We need to make sure that this view processes the files
    # In practice, processing will block the rendering of the template
    # So we might not be able to show the processing page before processing completes

    # Process the files (you may need to pass the file information via session or database)
    # For simplicity, let's assume we can retrieve the file information from the database

    # Retrieve the latest uploaded files
    pdf_instances = UploadedPDF.objects.all().order_by('-uploaded_at')[:5]  # Adjust as needed
    excel_dir = os.path.join(settings.MEDIA_ROOT, 'excel')
    excel_files = os.listdir(excel_dir)
    if excel_files:
        excel_file_path = os.path.join(excel_dir, excel_files[-1])  # Use the latest uploaded Excel file
    else:
        return HttpResponse("No Excel file uploaded.")

    process_uploaded_pdfs(pdf_instances, excel_file_path)

    return redirect('download_report')


def redirect_to_upload(request):
    return redirect('upload_files')



def cleanup_files(pdf_instances, excel_file_path):
    # Supprimer uniquement les nouveaux fichiers uploadés, pas les fichiers existants
    for pdf_instance in pdf_instances:
        if pdf_instance.batch == None:
            if os.path.exists(pdf_instance.file.path):
                os.remove(pdf_instance.file.path)
            pdf_instance.delete()

    # Si le fichier Excel est un nouveau fichier uploadé
    excel_dir = os.path.dirname(excel_file_path)
    if 'excel' in excel_dir:
        if os.path.exists(excel_file_path):
            os.remove(excel_file_path)
        # Supprimer l'instance UploadedExcel correspondante si nécessaire

    # Supprimer les fichiers de sortie si nécessaire
    output_dir = os.path.join(settings.MEDIA_ROOT, 'outputs')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)


@login_required
@require_POST
def delete_pdf(request):
    pdf_id = request.POST.get('pdf_id')
    if pdf_id:
        pdf_instance = get_object_or_404(UploadedPDF, id=pdf_id)
        pdf_instance.delete()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'ID de fichier PDF manquant'})
