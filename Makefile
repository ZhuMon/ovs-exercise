TOPO = topology.json
CONTROLLER = simple_switch_rest_13.py

MN_ARGS = -t $(TOPO) -c $(CONTROLLER)

ifdef REMOTE
    MN_ARGS += -r
endif

all: mininet

mininet:
	sudo python3 run_mininet.py $(MN_ARGS)

stop:
	sudo mn -c

clean: stop
	rm -f *.pyc
	sudo rm -rf __pycache__
