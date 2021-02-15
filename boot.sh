
# Update  mac address
./updateMac.sh

#Get current Path
export C_PATH=$(pwd)

setupApplication()
{
    tmux new-session -s fruit2pi -n pi_bluetooth -d
    tmux split-window -h -t fruit2pi
    tmux split-window -v -t fruit2pi
    tmux send-keys -t fruit2pi:pi_bluetooth.0 'cd $C_PATH/server && reset && sudo ./btk_server.py ' C-m
    tmux send-keys -t fruit2pi:pi_bluetooth.1 'cd $C_PATH/mouse  && reset ' C-m
    tmux send-keys -t fruit2pi:pi_bluetooth.2 'cd $C_PATH/keyboard  && reset ' C-m
}

STATUS=$(tmux ls 2>&1)

echo "STATUS: ${STATUS}"

if [ "${STATUS}" = "no server running on /tmp/tmux-1000/default" ] ; then
    echo "no tmux instance"
    setupApplication
else
    STATUS=$(tmux has-session -t  fruit2pi 2>&1)
    if [ "${STATUS}" = "can't find session fruit2pi" ] ; then
        echo "no session fruit2pi"
        setupApplication
    fi
fi