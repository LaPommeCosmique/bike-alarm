#ifndef WIFICLIENT_H
#define WIFICLIENT_H

class WifiClient
{
  public:
    WifiClient(char *ssid, char *pass);
    void connect();
    int getStatus();

  private:
    char *_ssid;
    char *_pass;
};

#endif