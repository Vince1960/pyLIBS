//---------------------------------------------------------------------------
#include <vcl.h>
#include <string.h>
#include <sys\stat.h>
#include <stdio.h>
#include <fcntl.h>
#include <io.h>
#include <alloc.h>
#include <stdlib.h>
#include <condefs.h>
#include <iostream.h>
#include <fstream.h>
#include <conio.h>
#include <math.h>
#include <sysdefs.h>
#include <dstring.h>
#include <Clipbrd.hpp>
#include "SDIMain.h"
#include "Unit4.h"
#include <vector.h>
#pragma hdrstop
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm4 *Form4;
//---------------------------------------------------------------------------
__fastcall TForm4::TForm4(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm4::Button1Click(TObject *Sender)
{
float shif=atof(Form4->Edit2->Text.c_str())-atof(Form4->Edit1->Text.c_str());
SDIAppForm->Series2->Clear();
for (int i=0; i < SDIAppForm->Series1->Count(); i++)
{
SDIAppForm->Series2->AddXY(SDIAppForm->Series1->XValues->Value[i],SDIAppForm->Series1->YValues->Value[i]+shif,' ',clBlack);
}
swap(SDIAppForm->Series2,SDIAppForm->Series1);
SDIAppForm->Series2->Active=false;
SDIAppForm->Series1->Active=true;
Form4->Close();
}
//---------------------------------------------------------------------------
 