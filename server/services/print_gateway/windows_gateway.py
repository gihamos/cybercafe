import sys
import tempfile
import time
from pathlib import Path

from services.print_gateway.base import PrintGateway, PrintJobResult


class WindowsGateway(PrintGateway):
    """Impression via le spouleur Windows (pywin32), en déléguant l'ouverture/rendu du
    document au verbe "print" associé au type de fichier (ex: le lecteur PDF par
    défaut pour un .pdf) — évite d'avoir à réimplémenter un moteur de rendu PDF/DOCX
    pour piloter l'imprimante en mode brut. Limite connue : le verbe "print" ne permet
    pas de transmettre directement le nombre de copies/le recto-verso/la couleur —
    seule la sélection de l'imprimante cible est forcée (imprimante par défaut
    temporairement basculée le temps de l'impression). ⚠️ Non testée sur une machine
    Windows réelle dans cet environnement de développement (pywin32 n'est installable
    que sous Windows) — à valider avant mise en production."""

    nom = "windows"

    def __init__(self):
        if sys.platform != "win32":
            raise ValueError("La passerelle d'impression Windows ne fonctionne que sur Windows")

    def _win32(self):
        import win32print
        import win32api
        return win32print, win32api

    def imprimer(
        self,
        contenu: bytes,
        nom_fichier: str,
        copies: int = 1,
        recto_verso: bool = False,
        couleur: bool = False,
        imprimante: str | None = None,
    ) -> PrintJobResult:
        win32print, win32api = self._win32()

        suffixe = Path(nom_fichier).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(suffix=suffixe, delete=False) as f:
            f.write(contenu)
            chemin = f.name

        cible = imprimante or win32print.GetDefaultPrinter()
        precedente = win32print.GetDefaultPrinter()
        bascule = cible != precedente
        if bascule:
            win32print.SetDefaultPrinter(cible)

        debut = time.time()
        try:
            for _ in range(max(1, copies)):
                win32api.ShellExecute(0, "print", chemin, None, ".", 0)
        finally:
            if bascule:
                win32print.SetDefaultPrinter(precedente)

        # Pas d'identifiant de job réel disponible via ShellExecute (asynchrone, géré
        # par l'application associée) : on encode l'imprimante + l'instant de soumission
        # pour retrouver le job correspondant dans la file lors du suivi de statut.
        job_id = f"{cible}|{debut}"
        return PrintJobResult(job_id=job_id, statut="en_file")

    def get_statut(self, job_id: str) -> PrintJobResult:
        win32print, _ = self._win32()
        try:
            imprimante, debut = job_id.split("|", 1)
            debut = float(debut)
        except ValueError:
            return PrintJobResult(job_id=job_id, statut="inconnu", message="Identifiant de job invalide")

        handle = win32print.OpenPrinter(imprimante)
        try:
            jobs = win32print.EnumJobs(handle, 0, -1, 1)
        finally:
            win32print.ClosePrinter(handle)

        # Le job soumis après notre horodatage sur cette imprimante — heuristique
        # nécessaire car ShellExecute ne renvoie pas l'identifiant réel du spouleur.
        candidats = [j for j in jobs if j.get("Submitted") and time.mktime(j["Submitted"].timetuple()) >= debut - 2]
        if not candidats:
            # le job n'est plus dans la file : soit pas encore soumis par l'appli
            # associée (PDF viewer en cours de lancement), soit déjà terminé
            return PrintJobResult(job_id=job_id, statut="termine")

        job = candidats[0]
        status = job.get("Status", 0)
        JOB_STATUS_ERROR = 0x00000002
        JOB_STATUS_PRINTED = 0x00000080
        JOB_STATUS_PRINTING = 0x00000010
        if status & JOB_STATUS_ERROR:
            return PrintJobResult(job_id=job_id, statut="erreur", message="Erreur d'impression signalée par le spouleur")
        if status & JOB_STATUS_PRINTED:
            return PrintJobResult(job_id=job_id, statut="termine")
        if status & JOB_STATUS_PRINTING:
            return PrintJobResult(job_id=job_id, statut="en_cours")
        return PrintJobResult(job_id=job_id, statut="en_file")

    def annuler(self, job_id: str) -> None:
        win32print, _ = self._win32()
        imprimante, _ = job_id.split("|", 1)
        handle = win32print.OpenPrinter(imprimante)
        try:
            jobs = win32print.EnumJobs(handle, 0, -1, 1)
            for job in jobs:
                win32print.SetJob(handle, job["JobId"], 0, None, win32print.JOB_CONTROL_CANCEL)
        finally:
            win32print.ClosePrinter(handle)

    def lister_imprimantes(self) -> list[str]:
        win32print, _ = self._win32()
        return [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
