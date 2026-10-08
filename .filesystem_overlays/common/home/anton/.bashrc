#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
# alias element='ELECTRON_ENABLE_SECURITY_KEYRING=1 element-desktop --password-store=kwallet6'
alias element-desktop='ELECTRON_ENABLE_SECURITY_KEYRING=1 element-desktop --password-store=kwalle>
# Function to get git branch
git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

PS1='[\[\033[32m\]\u\[\033[0m\]@\[\033[34m\]\h\[\033[0m\] \[\033[33m\]\W\[\033[36m\]$(git_branch)>

export SSH_AUTH_SOCK="$HOME/.1password/agent.sock"
export GPG_TTY=$(tty)

# export PATH=$PATH:/home/anton/.local/bin/
export PATH="$HOME/.local/bin:$PATH"
