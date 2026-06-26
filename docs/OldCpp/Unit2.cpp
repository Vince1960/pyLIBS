//---------------------------------------------------------------------------
#include <vcl.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit2.h"
#include "Unit5.h"
#include "Unit6.h"
#define COLORE 12632150
#pragma hdrstop
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm2 *Form2;
//---------------------------------------------------------------------------
__fastcall TForm2::TForm2(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm2::Button1Click(TObject *Sender)
{
  char lab[12];

 int rc,ind,ioniz;
 float maxnt,yval,maxscal;
 
if (StrLen(AnsiString(Form2->Edit1->Text).c_str()) == 1)
{
Form2->Edit1->Text=UpperCase(Form2->Edit1->Text);
}
else
{
 char ss[4];
   Form2->Edit3->Text =Form2->Edit1->Text[1];
   Form2->Edit4->Text =Form2->Edit1->Text[2];
 sprintf(ss,"%s%s",UpperCase(AnsiString(Form2->Edit3->Text).c_str()),AnsiString(Form2->Edit4->Text).c_str());
 Form2->Edit1->Text=ss;


 }
AnsiString spi= Form2->Edit1->Text + "+";
char sqls[300];
int sw;
sw=RadioGroup1->ItemIndex;
switch(sw)
{
case 0:
sprintf(sqls,"SELECT * FROM datalibs WHERE ([specie] = '%s' OR [specie] = '%s')and [wavelen] > %f and [wavelen] < %f and [ion]=1 order by -[inte]",AnsiString(Form2->Edit1->Text).c_str(),spi.c_str(),SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
 Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount == 0)
 return;


 rc=Form5->Query1->RecordCount;
  if (rc > atof(AnsiString(Form2->Edit2->Text).c_str()))
  rc= atof(AnsiString(Form2->Edit2->Text).c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();
break;
case 1:
sprintf(sqls,"SELECT * FROM datalibs WHERE ([specie] = '%s' OR [specie] = '%s') and [wavelen] > %f and [wavelen] < %f and [ion]=2 order by -[inte]",AnsiString(Form2->Edit1->Text).c_str(),spi.c_str(),SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
 Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount == 0)
 return;

 rc=Form5->Query1->RecordCount;
  if (rc > atof(AnsiString(Form2->Edit2->Text).c_str()))
  rc= atof(AnsiString(Form2->Edit2->Text).c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();
break;
case 2:
sprintf(sqls,"SELECT * FROM datalibs WHERE ([specie] = '%s' OR [specie] = '%s') and [wavelen] > %f and [wavelen] < %f order by -[inte]",AnsiString(Form2->Edit1->Text).c_str(),spi.c_str(),SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
 Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount == 0)
 return;

 rc=Form5->Query1->RecordCount;
  if (rc > atof(AnsiString(Form2->Edit2->Text).c_str()))
  rc= atof(AnsiString(Form2->Edit2->Text).c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();
break;
case 3:
sprintf(sqls,"SELECT * FROM datalibs WHERE ([specie] = '%s' OR [specie] = '%s') and [wavelen] > %f and [wavelen] < %f and [ion]=1 order by -[inte]",AnsiString(Form2->Edit1->Text).c_str(),spi.c_str(),SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount == 0)
 return;

 rc=Form5->Query1->RecordCount;
  if (rc > atof(AnsiString(Form2->Edit2->Text).c_str()))
  rc= atof(AnsiString(Form2->Edit2->Text).c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();

sprintf(sqls,"SELECT * FROM datalibs WHERE ([specie] = '%s' OR [specie] = '%s') and [wavelen] > %f and [wavelen] < %f and [ion]=2 order by -[inte]",AnsiString(Form2->Edit1->Text).c_str(),spi.c_str(),SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount == 0)
 return;
 rc=Form5->Query1->RecordCount;
  if (rc > atof(AnsiString(Form2->Edit2->Text).c_str()))
  rc= atof(AnsiString(Form2->Edit2->Text).c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();
break;
}
  SDIAppForm->Series5->Active=True;
  Form2->Show();
}
//---------------------------------------------------------------------------
void __fastcall TForm2::Button2Click(TObject *Sender)
{
SDIAppForm->Series5->Clear();
}
//---------------------------------------------------------------------------

void __fastcall TForm2::Button3Click(TObject *Sender)
{
 char sqls[300];
 TLocateOptions Opts;
  Opts.Clear();
   Opts << loPartialKey << loCaseInsensitive;
 SDIAppForm->Chart1->BottomAxis->Automatic=false;
  float range=atof(AnsiString(OKBottomDlg->Edit9->Text).c_str());
   float oldmin= SDIAppForm->Chart1->BottomAxis->Minimum;
  float oldmax= SDIAppForm->Chart1->BottomAxis->Maximum;
 float freqw;
 int findx=SDIAppForm->Series5->FirstValueIndex;
  int lindx=SDIAppForm->Series5->LastValueIndex;
  for(int k=findx; k < lindx+1; k++)
{
 char sqls[300];
   AnsiString spe,io,ppp,sp;
    int lg;
	float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
if (k < 0)
 break;

  freqw= SDIAppForm->Series5->XValues->Value[k];
  SDIAppForm->Chart1->BottomAxis->SetMinMax(freqw-range,freqw+range);
    SDIAppForm->Chart1->Refresh();
    int sm;
     float mind,dd;
     int s4f,s4l;

    if  (SDIAppForm->Series4->FirstValueIndex < 0)
     {
     goto pppp;
     }

     s4f=SDIAppForm->Series4->FirstValueIndex;
      s4l=SDIAppForm->Series4->LastValueIndex;

    if (s4f == s4l)
    {
    sm=s4f;
    }
    else if (s4l < s4f)
    {
    goto pppp;
    }
    else
    {
    sm=s4f;
    mind=1.e22;
    for (int z=s4f; z < s4l+1;z++)
    {
    dd=fabs(freqw-SDIAppForm->Series4->XValues->Value[z]);
    if (dd < mind)
    {
    mind=dd;
    sm=z;
    }
    }
    }



 

  Form6->Table1->RecNo=sm+1;


 if (Form6->Table1->FieldByName("Aki")->AsFloat >= soglia)
 {
 SDIAppForm->Series4->ValueColor[sm]=clYellow;
 }
 else
 {
  SDIAppForm->Series4->ValueColor[sm]=COLORE;
 }
 ppp=SDIAppForm->Series5->XLabel[k];

lg=StrLen(ppp.c_str());
 sp=ppp.SubString(lg-1,2);
 char label[10];
 if (sp != "II")
 {
  spe=ppp.SubString(1,lg-1);

  if (spe.SubString(lg-2,1)=="+")
        {
        spe=spe.SubString(1,lg-3);

        }
  io=AnsiString("1");
  sprintf(label,"%s I",spe);
  }
  else if ((sp=="II") & (lg==2))
 {
    spe="I";
     io=AnsiString("1");
     sprintf(label,"I I");
 }
 else
 {
 spe=ppp.SubString(1,lg-2);
 if (spe.SubString(lg-3,1)=="+")
        {
        spe=spe.SubString(1,lg-4);

        }
 io=AnsiString("2");
 sprintf(label,"%s II",spe);
 }

 SDIAppForm->Series4->XLabel[sm]=label;


  Form5->Edit1->Text=SDIAppForm->Series5->XValues->Value[k];
  Form5->Edit2->Text= spe;
  Form5->Edit3->Text= io;

  sprintf(sqls,"SELECT * FROM %s WHERE [ion]=%s AND [wavelen] BETWEEN %f-0.04 AND %f+0.04", AnsiString(Form5->Edit2->Text).c_str(),AnsiString(Form5->Edit3->Text).c_str(),atof(AnsiString(Form5->Edit1->Text).c_str()),atof(AnsiString(Form5->Edit1->Text).c_str()));

  Form5->Query2->SQL->Clear();
   Form5->Query2->SQL->Add(sqls);
     Form5->Query2->Open();
      Form5->Query2->First();
 SDIAppForm->Edit4->Text=FormatFloat("#0000.00",SDIAppForm->Series4->XValues->Value[sm]);
    if (Form5->Query2->RecordCount == 0)
    {
    }
else
{
 if (Form6->Table1->Locate("fitwavelen",SDIAppForm->Series4->XValues->Value[sm],Opts))
  {
  }
  else if (Form6->Table1->Locate("wavelen",SDIAppForm->Series4->XValues->Value[sm],Opts))
  {
  }
  else if (Form6->Table1->Locate("wavelen",SDIAppForm->Edit4->Text,Opts))
  {
  }
   else if (Form6->Table1->Locate("fitwavelen",SDIAppForm->Edit4->Text,Opts))
  {
  }
  else
  {
  // ShowMessage(SDIAppForm->Edit4->Text);
  }
Form6->Table1->Edit();
Form6->Table1->FieldValues["specie"]=AnsiString(Form5->Edit2->Text).c_str();
Form6->Table1->FieldValues["ion"]=Form5->Query2->FieldValues["ion"];
Form6->Table1->FieldValues["asswavelen"]=Form5->Query2->FieldByName("wavelen")->AsFloat;
Form6->Table1->FieldValues["Ek"]=Form5->Query2->FieldByName("Ek")->AsFloat;
Form6->Table1->FieldValues["acc"]=Form5->Query2->FieldValues["acc"];
if (Form6->Table1->FieldValues["Aki"] == -1.0)
{
if (Form5->Query2->FieldByName("Aki")->AsFloat !=0.0)
{
Form6->Table1->FieldValues["Aki"]=-Form5->Query2->FieldByName("Aki")->AsFloat;
}
else
{
Form6->Table1->FieldValues["Aki"]=-Form5->Query2->FieldByName("Aki")->AsFloat;
}
}
else
{
Form6->Table1->FieldValues["Aki"]=Form5->Query2->FieldByName("Aki")->AsFloat;
}
Form6->Table1->FieldValues["gk"]=Form5->Query2->FieldValues["gk"];
Form6->Table1->FieldValues["gi"]=Form5->Query2->FieldValues["gi"];
  Form6->Table1->Refresh();
// }
 //Form5->Query1->Next();
}
pppp:
}
 //  Form5->Query1->First();
  SDIAppForm->Chart1->BottomAxis->SetMinMax(oldmin,oldmax);
  SDIAppForm->Series5->Active=True;
  SDIAppForm->Series5->Clear();
}
//---------------------------------------------------------------------------



