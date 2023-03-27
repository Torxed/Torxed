## Key management

// https://makandracards.com/makandra-orga/37763-gpg-extract-private-key-and-import-on-different-machine

```bash
$ gpg2 --import anton.hvornum.private.key
```

## Git config

```
$ gpg --list-secret-keys --keyid-format=long | grep 'sec>'
$ git config --global user.signingkey 5FBBB32941E3740A
$ export GPG_TTY=$(tty)
$ echo 'export GPG_TTY=$(tty)' >> ~/.bashrc
```

## Notes

Just a small reminder of how to move the HSM between the machines
