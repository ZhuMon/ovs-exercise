# ovs-exercise

## Usage
* default
    ```
    $ make
    ```

* customize
    ```
    $ make TOPO=topology.json CONTORLLER=simple_switch_13.py
    ```

* pass packets
    * At h2 xterm
        ```
        h2 # ./receive.py
        ```
    * At h1 xterm
        ```
        h1 # ./send.py 10.0.0.2 "hello"
        ```

* web application http://127.0.0.1/main




