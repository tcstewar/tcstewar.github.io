class PeerStack {
    constructor() {
        this.items = [];
        this.metadata = {}
        this.index = 0;
    }
    
    init() { 
        self = this;
        this.clients = [];
        this.peer = new Peer();
        this.peer.on('open', () => {$(self).trigger('open');});
        this.peer.on('connection', (conn) => {self.on_connect_from_client(conn);});
        this.peer.on('error', () => {console.log('error');});
        this.is_host = true;  
        this.is_connecting = false;        
        return this;
    }
        
    connect_to(host) {
        self = this;
        this.is_connecting = true;
        this.conn = this.peer.connect(host, {reliable:true});
        this.conn.on('open', () => {self.on_connect_to_host();});
        this.conn.on('error', () => {console.log('error');});
        
        // no idea why this fails to give either open or error sometimes, so try again
        setTimeout(() => {  if (self.is_connecting) self.connect_to(host);}, 2000);         
    }
    
    on_connect_to_host() {
        this.is_connecting = false;
        this.conn.on('data', (data) => {self.received_data(data, self.conn);});
        this.conn.send({type:"get-all"});
        this.is_host = false;
        this.items = [];
    }
    
    received_data(data, conn) {
        if (data.type == 'item') {
            if (this.is_host) {
                this.add(data.value);
            } else {
                this.items.push(data.value);
                $(this).trigger('added');
            }
        } else if (data.type == 'get-all') {
            console.log(conn);
            console.log(this.clients);
            conn.send({type:"all", 
                       value:this.items, 
                       metadata:this.metadata,
                       index:this.clients.findIndex((item) => item == conn)+1,
                      });
        } else if (data.type == 'all') {
            this.metadata = data.metadata;
            this.items = data.value;
            this.index = data.index;
            $(this).trigger('changed');
        } else if (data.type == 'undo') {
            this.undo();
        }
    }
    
    on_connect_from_client(conn) {
        self = this;
        this.clients.push(conn);
        conn.on('data', (data) => {self.received_data(data, conn);});
    }
        
        

    add(item) {
        if (this.is_host) {
            this.send_to_clients({type:"item", index:this.items.length, value:item});
            this.items.push(item);
            $(this).trigger('added');
        } else {
            this.conn.send({type:"item", index:this.items.length, value:item});
        }
    }
    
    send_to_clients(msg) {
        for (var i in this.clients) {
            this.clients[i].send(msg);
        }        
    }
    
    undo() {
        if (this.is_host) {
            if (this.items.length > 0) {                
                this.items.pop();
                this.send_to_clients({type:"all", value:this.items, metadata:this.metadata});
                $(this).trigger('changed');
            }
        } else {
            this.conn.send({type:"undo"});
        }
    }
            
    
    on(ev, func) {
        $(this).on(ev, func);
        return this;
    }
}

