/*
FIXME
$ screen -R -d -S subtitles
Directory '/run/screen' must have mode 777.
*/

{ pkgs ? import <nixpkgs> { } }:

with pkgs;

mkShell {

  buildInputs = [
    nano # 2.7.4 -> 7.2
    git # 2.11.0 -> 2.44.0 # old git hangs at "resolving deltas"
    #gnumake
    python3 # 3.5 -> 3.11
    python3.pkgs.qbittorrent-api
    python3.pkgs.requests
    python3.pkgs.aiohttp
    python3.pkgs.libtorrent-rasterbar
    python3.pkgs.psutil
    python3.pkgs.torf
    python3.pkgs.deluge-client
    /*
    (python3.pkgs.callPackage ./nix/torf.nix {
      flatbencode = python3.pkgs.callPackage ./nix/flatbencode.nix { };
    })
    */
    nur.repos.milahu.python3.pkgs.torf

    tree-sitter
    (pkgs.python3.pkgs.callPackage ./nix/tree-sitter { })

    # FIXME no internet access
    # https://github.com/arvidn/libtorrent/issues/7926
    # workaround: run qbittorrent-nox in a container with eth0 (or similar)
    # https://www.feralhosting.com/wiki/software/qbittorrent
    #qbittorrent-nox
    #nur.repos.milahu.python3.pkgs.rtorrent-rpc
    nixpkgs-fmt
    coreutils-full # numfmt
    jq
    mmv # TODO prefer rename
    rename
    
    #ejabberd
    # irc server with websockets
    # https://ircv3.net/specs/extensions/websocket
    #unrealircd # not in nixpkgs
    #inspircd
    #ergochat
    
    # bittorrent
    rqbit
    #(callPackage ./nix/rqbit.nix { })
    #torrenttools
    aria2
    #qbittorrent-enhanced-nox
    qbittorrent-nox

    ffmpeg
    cpulimit

    # socks5 proxy server
    dante

    fdupes

    nettools # netstat
    nmap
  ];

  shellHook = ''
    # fix: Error in /etc/nanorc on line 166: Unknown option: suspend
    extra_nanorc="$(cat <<EOF
    # continue indent level of last line
    set autoindent
    # indent with 2 spaces
    set tabstospaces
    set tabsize 2
    EOF
    )"
    if ! [ -e ~/.nanorc ]; then
      cp /etc/nanorc ~/.nanorc
      chmod +w ~/.nanorc
      sed -i 's/^set suspend/# &/' ~/.nanorc
      echo "$extra_nanorc" >>~/.nanorc
    fi
    alias nano='nano --rcfile=~/.nanorc'
  '';
}
