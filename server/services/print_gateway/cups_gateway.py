import subprocess
import tempfile
from pathlib import Path

from services.print_gateway.base import PrintGateway, PrintJobResult


class CupsGateway(PrintGateway):
    """Impression via CUPS (Linux/macOS), en passant par les utilitaires en ligne de
    commande `lp`/`lpstat`/`lprm` (paquet cups-client) plutôt qu'une dépendance C
    (pycups) — CUPS accepte nativement PDF, PostScript, texte et la plupart des
    formats image, ce qui couvre les documents envoyés depuis le portail/le kiosque
    sans traitement supplémentaire. ⚠️ Non testée contre une vraie imprimante dans cet
    environnement de développement (aucun service CUPS disponible dans ce sandbox) —
    à valider sur une machine avec `cups-client` installé et au moins une imprimante
    configurée avant mise en production."""

    nom = "cups"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=30)
        except FileNotFoundError as e:
            raise ValueError(
                f"Commande '{args[0]}' introuvable — le paquet cups-client est-il installé ? ({e})"
            )

    def imprimer(
        self,
        contenu: bytes,
        nom_fichier: str,
        copies: int = 1,
        recto_verso: bool = False,
        couleur: bool = False,
        imprimante: str | None = None,
    ) -> PrintJobResult:
        suffixe = Path(nom_fichier).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(suffix=suffixe, delete=False) as f:
            f.write(contenu)
            chemin = f.name

        args = ["lp", "-n", str(max(1, copies))]
        if imprimante:
            args += ["-d", imprimante]
        if recto_verso:
            args += ["-o", "sides=two-sided-long-edge"]
        else:
            args += ["-o", "sides=one-sided"]
        if not couleur:
            args += ["-o", "print-color-mode=monochrome"]
        args.append(chemin)

        result = self._run(*args)
        if result.returncode != 0:
            return PrintJobResult(job_id="", statut="erreur", message=result.stderr.strip() or "Échec de soumission à CUPS")

        # sortie attendue : "request id is PRINTERNAME-123 (1 file(s))"
        sortie = result.stdout.strip()
        job_id = sortie.split()[3] if len(sortie.split()) >= 4 else sortie
        return PrintJobResult(job_id=job_id, statut="en_file")

    def get_statut(self, job_id: str) -> PrintJobResult:
        en_attente = self._run("lpstat", "-o", job_id)
        if job_id in en_attente.stdout:
            return PrintJobResult(job_id=job_id, statut="en_cours")

        annules = self._run("lpstat", "-W", "not-completed", "-o", job_id)
        if job_id in annules.stdout:
            return PrintJobResult(job_id=job_id, statut="en_cours")

        # CUPS purge rapidement sa file : absent de la file = imprimé (ou purgé après
        # erreur non détectable en ligne de commande — cas rare, considéré terminé).
        return PrintJobResult(job_id=job_id, statut="termine")

    def annuler(self, job_id: str) -> None:
        result = self._run("lprm", job_id)
        if result.returncode != 0 and "not found" not in (result.stderr or "").lower():
            raise ValueError(f"Impossible d'annuler le job {job_id} : {result.stderr.strip()}")

    def lister_imprimantes(self) -> list[str]:
        result = self._run("lpstat", "-p")
        noms = []
        for ligne in result.stdout.splitlines():
            if ligne.startswith("printer "):
                noms.append(ligne.split()[1])
        return noms
