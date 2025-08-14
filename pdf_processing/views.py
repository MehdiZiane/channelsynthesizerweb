import os
import shutil
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import UploadFilesForm
from .models import UploadedPDF, UploadedExcel, ProcessingBatch
from .processing import process_uploaded_pdfs
from image_processing.services import analyze_pdf_images


@login_required
def upload_files(request):
    if request.method == "POST":
        form = UploadFilesForm(request.POST, request.FILES)
        if form.is_valid():
            include_base_offers = form.cleaned_data.get("include_base_offers", False)
            batch = ProcessingBatch.objects.create()

            pdf_files = request.FILES.getlist("pdf_files")
            existing_pdf_files = form.cleaned_data.get("existing_pdf_files", [])
            excel_file = request.FILES.get("excel_file")
            existing_excel_file = form.cleaned_data.get("existing_excel_file")

            pdf_instances_for_processing = []

            # Traiter les nouveaux fichiers PDF
            for pdf_f in pdf_files:
                pdf_instance = UploadedPDF(file=pdf_f, batch=batch)
                pdf_instance.save()
                pdf_instances_for_processing.append(pdf_instance)

            # Traiter les fichiers PDF existants
            for pdf_inst in existing_pdf_files:
                pdf_inst.batch = batch
                pdf_inst.save()
                pdf_instances_for_processing.append(pdf_inst)

            # --- CORRECTION POUR LA GESTION DES FICHIERS CLOUD ---
            excel_file_path_temp = None
            try:
                # Gérer le fichier Excel
                if excel_file:
                    excel_instance = UploadedExcel(file=excel_file)
                    excel_instance.save()
                    batch.excel_file = excel_instance
                elif existing_excel_file:
                    batch.excel_file = existing_excel_file
                else:
                    raise ValueError("Aucun fichier Excel fourni.")
                batch.save()

                # On ouvre le fichier (qu'il soit local ou sur Azure) et on le copie localement
                # dans un fichier temporaire pour que les parsers puissent le lire.
                excel_to_process = batch.excel_file
                with excel_to_process.file.open("rb") as f_in:
                    # Crée un fichier temporaire qui sera supprimé à la fermeture
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".xlsx"
                    ) as temp_f_out:
                        temp_f_out.write(f_in.read())
                        excel_file_path_temp = temp_f_out.name

                # Lancer l'analyse d'images (cette fonction semble prendre des objets, c'est ok)
                print("--- Lancement de l'analyse d'images pour le batch ---")
                for pdf in pdf_instances_for_processing:
                    try:
                        analyze_pdf_images(pdf)
                    except Exception as e:
                        print(
                            f"Erreur majeure lors de l'analyse d'images pour {pdf.file.name}: {e}"
                        )
                print("--- Analyse d'images terminée pour le batch. ---")

                # Lancer le traitement principal avec les objets et le chemin du fichier temporaire
                process_uploaded_pdfs(
                    pdf_instances_for_processing,
                    excel_file_path_temp,
                    include_base_offers,
                )

                return redirect("download_report")

            finally:
                # S'assurer que le fichier temporaire est toujours supprimé
                if excel_file_path_temp and os.path.exists(excel_file_path_temp):
                    os.remove(excel_file_path_temp)
            # --- FIN DE LA CORRECTION ---
    else:
        form = UploadFilesForm()

    return render(request, "pdf_processing/upload_files.html", {"form": form})


# Le reste de vos vues (download_report, etc.) reste inchangé.
def download_report(request):
    reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
    report_file = os.path.join(reports_dir, "consolidated_report.xlsx")
    if os.path.exists(report_file):
        with open(report_file, "rb") as fh:
            response = HttpResponse(
                fh.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                "attachment; filename=" + os.path.basename(report_file)
            )
            return response
    else:
        return HttpResponseNotFound("The report is not available.")


@login_required
@require_POST
def delete_pdf(request):
    pdf_id = request.POST.get("pdf_id")
    if pdf_id:
        pdf_instance = get_object_or_404(UploadedPDF, id=pdf_id)
        # Il faut aussi supprimer le fichier sur Azure Storage
        pdf_instance.file.delete(save=True)  # save=True met à jour l'instance
        pdf_instance.delete()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False, "error": "ID de fichier PDF manquant"})


# Les autres vues (redirect_to_upload, etc.) que vous aviez peuvent être gardées si vous en avez l'utilité
def redirect_to_upload(request):
    return redirect("upload_files")
