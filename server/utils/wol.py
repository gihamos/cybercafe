import socket


def envoyer_magic_packet(mac_adresse: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> None:
    """Envoie un paquet magique Wake-on-LAN pour réveiller un poste éteint. Nécessite que
    la carte réseau du poste ait le WOL activé au niveau BIOS/OS — hors du contrôle de ce
    logiciel, à configurer une fois sur chaque poste."""
    mac_bytes = bytes.fromhex(mac_adresse.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError("Adresse MAC invalide")

    magic_packet = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, port))
