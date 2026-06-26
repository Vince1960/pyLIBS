//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include <dos.h>
#include <stdio.h>
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit3.h"
#include "Unit4.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit7.h"
#include "Unit8.h"
#include "Unit9.h"
#include "Unit10.h"
#include "Unit15.h"
#include "Unit16.h"
#include "Unit23.h"
#include "Unit26.h"
#include "Unit20.h"
#include <math.h>
#include <dir.h>
#define COLORE 12632150
#include "Unit27.h"
#include "Unit37.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma link "Chart"
#pragma link "TeEngine"
#pragma link "TeeProcs"
#pragma resource "*.dfm"
TForm37 *Form37;
//---------------------------------------------------------------------------
__fastcall TForm37::TForm37(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm37::Button1Click(TObject *Sender)
{
void replot();
void csigma();

double Ne(float,float,float);
   float tmin=atof(AnsiString(OKBottomDlg->Edit20->Text).c_str());
  float tmax=atof(AnsiString(OKBottomDlg->Edit21->Text).c_str());
float oldtemp,newtemp;
float contr,Neold;

	  Form37->Refresh();
		  csigma();
}
//---------------------------------------------------------------------------



void __fastcall TForm37::FormShow(TObject *Sender)
{
	   Form37->StringGrid2->ColWidths[0]=20;
	   Form37->StringGrid2->ColWidths[1]=30;
	   Form37->StringGrid2->ColWidths[2]=50;
	   Form37->StringGrid2->ColWidths[3]=50;
		Form37->StringGrid2->Cells[1][0]="Elem.";
		Form37->StringGrid2->Cells[2][0]="C(w%)";
		Form37->StringGrid2->Cells[3][0]="C(n%)";

}
//---------------------------------------------------------------------------
   void csigma()
		{
		#define SQR(a) ((a)*(a))
   int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
   double zZ(AnsiString spp,int ion,float ti);
		// Carica curva taratura

	  Form9->Chart1->ApplyZOrder=false;
		Form9->Chart1->BottomAxis->Automatic=true;
		Form9->Chart1->LeftAxis->Automatic=true;
		if ((OKBottomDlg->CheckBox2->Checked==true))
				{

				float xf,yf;
				Form10->Series1->Active=true;
				Form10->Series1->Clear();

                FILE *strm;
				strm = fopen(AnsiString(OKBottomDlg->Edit10->Text).c_str(), "rt");
                do
						{
                        fscanf(strm,"%g %g", &xf, &yf);
						if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
                                {
								xf=xf*10.0;
								}
						Form10->Series1->AddXY(xf,yf,' ',clBlack);
                        }
				while(!feof(strm));
				fclose(strm);
				 Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
				}
        else
				{
				Form10->Series1->Clear();
				Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
				}
        // Fine caricamento taratura


		float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
        char sqls[300];char sname[32];

		Form9->StringGrid1->RowCount=128;
	   Form9->StringGrid2->RowCount=64;

		int I, J;
        for (I = 1; I < Form9->StringGrid1->ColCount; I++)
		for (J = 1; J < Form9->StringGrid1->RowCount; J++)
                Form9->StringGrid1->Cells[I][J] = "";
		for (I = 1; I < Form9->StringGrid2->ColCount; I++)
        for (J = 1; J < Form9->StringGrid2->RowCount; J++)
				Form9->StringGrid2->Cells[I][J] = "";
		Form9->ComboBox1->Clear();
        Form9->ComboBox2->Clear();
        while (Form9->Chart1->SeriesCount()>0)
				{
                Form9->Chart1->Series[0]->Free();
				}

		   while (Form37->Chart1->SeriesCount()>0)
				{
				Form37->Chart1->Series[0]->Free();
				}

        Form9->StringGrid1->ColWidths[0]=20;
        Form9->StringGrid1->Cells[1][0]="Spec.";
		Form9->StringGrid1->Cells[2][0]="Lines";
		Form9->StringGrid1->Cells[3][0]="kT";
        Form9->StringGrid1->Cells[4][0]="q";
        Form9->StringGrid1->Cells[5][0]="Z(T)";

		sprintf(sqls,"SELECT DISTINCT SPECIE,ION FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
		Form9->Query1->Active=false;
		Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
		Form9->Query1->Active=true;
		Form9->Query1->SQL->Clear();
		Form9->Query1->SQL->Add(sqls);
		Form9->Query1->Open();
        Form9->Query1->First();
        Form9->Query2->Active=false;
        Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
		Form9->Query2->Active=true;
		sprintf(sqls,"SELECT DISTINCT SPECIE FROM %s WHERE aki != 0.0 AND aki !=-1.0 AND inte > 0.0 ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
		Form9->Query2->SQL->Clear();
		Form9->Query2->SQL->Add(sqls);
		Form9->Query2->Open();
        Form9->Query2->First();

		Form9->StringGrid2->ColWidths[0]=20;
		Form9->StringGrid2->Cells[1][0]="Elem.";
		Form9->StringGrid2->Cells[2][0]="Num %";
        Form9->StringGrid2->Cells[3][0]="Mass %";
		Form9->StringGrid2->Cells[4][0]="Ne";
        Form9->StringGrid2->Cells[5][0]="I/(I+II)";


		for (int rcu=0; rcu < Form9->Query2->RecordCount;rcu++)
                {
                Form9->Edit3->Text=Form9->Query2->FieldByName("specie")->AsString;
                Form9->StringGrid2->Cells[1][rcu+1]=Form9->Edit3->Text;
				Form9->ComboBox2->Items->Add(Form9->Edit3->Text);
                Form9->Query2->Next();
                }
		Form9->Query2->First();
		Form9->Query1->First();


        for (int i=0; i < Form9->Query1->RecordCount; i++)
				{
                TPointSeries *MySeries = new TPointSeries(Form9);
				MySeries->XValues->Order = loNone;
                MySeries->ParentChart=Form9->Chart1;

				Form9->Edit3->Text=Form9->Query1->FieldByName("specie")->AsString;
				Form9->Edit4->Text=Form9->Query1->FieldByName("ion")->AsString;
				int ioniz=Form9->Query1->FieldByName("ion")->AsInteger;

                switch(ioniz)
                        {
                        case 1:
						sprintf(sname,"%sI",AnsiString(Trim(Form9->Edit3->Text).c_str()));
                        break;
                        case 2:
						sprintf(sname,"%sII",AnsiString(Trim(Form9->Edit3->Text).c_str()));
						break;
						}

				Form9->StringGrid1->Cells[1][i+1]=sname;

				Form9->ComboBox1->Items->Add(sname);
                Form9->Query3->Active=false;
				Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);

                Form9->Query3->Active=true;
                Form9->Query6->Active=false;
                Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
				Form9->Query6->Active=true;
				MySeries->Name=sname;
				MySeries->Cursor=crHandPoint;

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki != 0.0 AND aki !=-1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),AnsiString(Form9->Edit3->Text).c_str(),AnsiString(Form9->Edit4->Text).c_str());
				Form9->Query3->SQL->Clear();
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
				Form9->Query3->SQL->Add(sqls);
				Form9->Query3->Open();
                Form9->Query3->First();
				Form9->StringGrid1->Cells[2][i+1]=Form9->Query3->RecordCount;

				for (int j=0; j < Form9->Query3->RecordCount; j++)
						{
						float wave=Form9->Query3->FieldValues["wavelen"];
                        float asswave=Form9->Query3->FieldValues["asswavelen"];
						float inte=Form9->Query3->FieldValues["inte"];
						float erro=Form9->Query3->FieldValues["error-inte"];
                        float aki= Form9->Query3->FieldValues["aki"];
                        int gk= Form9->Query3->FieldValues["gk"];
						float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                        float yyy;

						if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
										{
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
												yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
												(wave-Form10->Series1->XValues->Value[k]);
                                                goto aaa;
                                                }
										}
                                }
                        else
								{
                                yyy=1.0;
                                }
						aaa:

						 float sac=0;
						   for (int z=1; z < Form23->StringGrid1->RowCount;z++)
                             {
								if (fabs(atof(AnsiString(Form23->StringGrid1->Cells[2][z]).c_str())-asswave)<0.04)
								{
								 sac=atof(AnsiString(Form23->StringGrid1->Cells[3][z]).c_str());
                                 break;
								}
                                }
                              if (sac==0) sac=1;

					   inte/=(yyy*sac);
                        erro/=yyy;
						Form9->Chart1->Series[i]->Active=true;

                        float yy=log(inte/fabs(aki*gk));
						// float erl=erro/inte;
                        float erl=0.1;
						char wa[20];
						sprintf(wa,"%4.2e",erl);

                        if (aki > soglia)
								{
                                Form9->Chart1->Series[i]->SeriesColor=colo[i];
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,clTeeColor);
								}
                        else
                                {
								Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,COLORE);
                                }

						Form9->Query3->Next();
                        }
                Form9->Query1->Next();
				}
						Form9->Query2->Next();


	   // C-sigma

	   Form37->StringGrid2->ColWidths[0]=20;
	   Form37->StringGrid2->ColWidths[1]=30;
	   Form37->StringGrid2->ColWidths[2]=50;
	   Form37->StringGrid2->ColWidths[3]=50;
		Form37->StringGrid2->Cells[1][0]="Elem.";
		Form37->StringGrid2->Cells[2][0]="C(w%)";
		Form37->StringGrid2->Cells[3][0]="C(n%)";



		float tem=AnsiString(Form37->Edit7->Text).ToDouble();
		   float ne=AnsiString(Form37->Edit8->Text).ToDouble();

		   		sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0  ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),soglia);
		Form9->Query2->SQL->Clear();
		Form9->Query2->SQL->Add(sqls);
		Form9->Query2->Open();
		Form9->Query2->First();

		int spet=Form9->Query2->RecordCount;
				float ntot=0;
						for (int j=1; j <= spet;j++)
			   {
			   AnsiString ppp=Form9->Query2->FieldValues["specie"];
				Form37->StringGrid2->Cells[1][j]=ppp;
		 if (AnsiString(Form37->StringGrid2->Cells[2][j])=="") Form37->StringGrid2->Cells[2][j]=100/spet;
				sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",ppp);
				Form9->Query5->SQL->Clear();
				Form9->Query5->SQL->Add(sqls);
				Form9->Query5->Open();
						float massa=Form9->Query5->FieldValues["m_atomica"];
				ntot+= AnsiString(Form37->StringGrid2->Cells[2][j]).ToDouble()/massa;
				Form9->Query5->Close();
				Form9->Query2->Next();
				}
            						for (int j=1; j <= spet;j++)
			   {
			   AnsiString ppp = Form37->StringGrid2->Cells[1][j];
			   sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",ppp);
				Form9->Query5->SQL->Clear();
				Form9->Query5->SQL->Add(sqls);
				Form9->Query5->Open();
						float massa=Form9->Query5->FieldValues["m_atomica"];
				  Form37->StringGrid2->Cells[3][j]= AnsiString(Form37->StringGrid2->Cells[2][j]).ToDouble()/massa/ntot*100.;
				Form9->Query5->Close();
				}

		sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0  ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),soglia);
		Form9->Query2->SQL->Clear();
		Form9->Query2->SQL->Add(sqls);
		Form9->Query2->Open();
		Form9->Query2->First();
		int spetot=Form9->Query2->RecordCount;

		double saha,eion;
		int jj=0;



		for (int i=0; i < spetot;i++)
				{

				AnsiString ppp=Form9->Query2->FieldValues["specie"];


						sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'", ppp);
						Form9->Query5->SQL->Clear();
                        Form9->Query5->SQL->Add(sqls);
						Form9->Query5->Open();
						eion=Form9->Query5->FieldValues["en_ion"]*0.000123985;
						float z1=zZ(ppp,1,tem);
						float z2=zZ(ppp,2,tem);

	saha=(6.04e+21)/ne*z2/z1*pow(tem,1.5)*exp(-eion/tem);
	float f1=1./(1.+saha);
	 float f2=saha/(1.+saha);

				// Cerco Neutri

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=1 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
				Form9->Query6->SQL->Clear();
				Form9->Query6->SQL->Add(sqls);
				Form9->Query6->Open();
				Form9->Query6->First();
				int lin1=Form9->Query6->RecordCount;
				if (lin1 >0) {

				sprintf(sname,"%sI",AnsiString(Trim(ppp)).c_str());

                jj++;


			 //			Form37->StringGrid2->Cells[1][jj]=Form9->StringGrid1->Cells[1][i+1];
						 TPointSeries *MySeries = new TPointSeries(Form37);
							 MySeries->ParentChart=Form37->Chart1;
							 MySeries->Name=sname;
			 //				 Form37->StringGrid2->Cells[1][jj]=sname;
			 //        	if (AnsiString(Form37->StringGrid2->Cells[2][jj])=="") Form37->StringGrid2->Cells[2][jj]=100;
							  MySeries->Cursor=crHandPoint;

                 sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=1 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
				   Form9->Query6->SQL->Clear();
				   Form9->Query6->SQL->Add(sqls);
				   Form9->Query6->Open();
					   Form9->Query6->First();
					   float inte1,inte2,e1,e2,gi1,gi2,gk1,gk2,ekk,ratio;
					   for (int i=0; i <lin1;i++)
						{
						float wave=Form9->Query6->FieldValues["wavelen"];
						float asswave=Form9->Query6->FieldValues["asswavelen"];
						float gi1=Form9->Query6->FieldValues["gi"];
						float gk1=Form9->Query6->FieldValues["gk"];
						float inte1=Form9->Query6->FieldValues["inte"];
						float ak1=Form9->Query6->FieldValues["aki"];
						float e1= Form9->Query6->FieldValues["Ek"]*1.23985e-4;
						float ion= Form9->Query6->FieldValues["ion"];

						sprintf(sqls,"SELECT Ei FROM %s WHERE ion=%i AND [wavelen] BETWEEN %f AND %f",ppp,1,asswave-0.04,asswave+0.04);
						Form9->Query7->SQL->Clear();
						Form9->Query7->SQL->Add(sqls);
						Form9->Query7->Open();
						Form9->Query7->First();
						float Ei=(Form9->Query7->FieldByName("Ei")->AsFloat)*1.23985e-4;

						float yyy=1.0;
                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
								{
								for (int k=0; k < Form10->Series1->Count(); k++)
										{
										if (wave < Form10->Series1->XValues->Value[k])
												{
												yyy=Form10->Series1->YValues->Value[k]+
												(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
												(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
												(wave-Form10->Series1->XValues->Value[k]);
												break;
												}
										}
								}
						else
								{
								yyy=1.0;
								}

						float delta=0.01;

						sprintf(sqls,"SELECT * FROM Stark where [Element] = '%s' and [Ion] = %i and ([Wavelength] between %f and %f )", ppp, 1,asswave-delta,asswave+delta);


						Form37->Query1->SQL->Clear();
						Form37->Query1->SQL->Add(sqls);
						Form37->Query1->Open();
						   Form37->Query1->First();


						float w5000=Form37->Query1->FieldByName("w-T5000")->AsFloat;
						float w10000=Form37->Query1->FieldByName("w-T10000")->AsFloat;


						float ws=w5000+(w10000-w5000)*(tem-5000.)/5000.;

						 float Dl=ws*2.*ne/1.e17*1.e-8;

						if (Dl==0) Dl=0.01*2.*ne/1.e17*1.e-8;
							 float wcm=(asswave*1.e-8);
							   inte1/=yyy/Dl*1e30;
							ekk=1e17*pow(wcm,4)*f1*AnsiString(Form37->StringGrid2->Cells[3][jj]).ToDouble()*gk1*ak1*exp(-Ei/tem)/z1*(1.-exp(-(e1-Ei)/tem));
							MySeries->AddXY(ekk,inte1);
						  Form9->Query6->Next();
						  }
					}


				// Cerco Ionizzati

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=2 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
				Form9->Query3->SQL->Clear();
				Form9->Query3->SQL->Add(sqls);
				Form9->Query3->Open();
				Form9->Query3->First();
				int lin2=Form9->Query3->RecordCount;

				if (lin2 >0) {

				sprintf(sname,"%sII",AnsiString(Trim(ppp)).c_str());



						jj++;


						  //	Form37->StringGrid2->Cells[1][jj]=Form9->StringGrid1->Cells[1][i+1];
						 TPointSeries *MySeries = new TPointSeries(Form37);
							 MySeries->ParentChart=Form37->Chart1;
							 MySeries->Name=sname;
						   //	 Form37->StringGrid2->Cells[1][jj]=sname;
	   //	if (AnsiString(Form37->StringGrid2->Cells[2][jj])=="") Form37->StringGrid2->Cells[2][jj]=100;
							  MySeries->Cursor=crHandPoint;


                   float sac;

				   sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
				   Form9->Query6->SQL->Clear();
				   Form9->Query6->SQL->Add(sqls);
				   Form9->Query6->Open();
					   Form9->Query6->First();
					   float inte1,inte2,e1,e2,gi1,gi2,gk1,gk2,ekk,ratio;
					   for (int i=0; i <lin2;i++)
						{
						float wave=Form9->Query6->FieldValues["wavelen"];
						float asswave=Form9->Query6->FieldValues["asswavelen"];
						float gi1=Form9->Query6->FieldValues["gi"];
						float gk1=Form9->Query6->FieldValues["gk"];
						float inte1=Form9->Query6->FieldValues["inte"];
						float ak1=Form9->Query6->FieldValues["aki"];
						float e1= Form9->Query6->FieldValues["Ek"]*1.23985e-4;
						float ion= Form9->Query6->FieldValues["ion"];
						sprintf(sqls,"SELECT Ei FROM %s WHERE ion=%i AND [wavelen] BETWEEN %f AND %f",ppp,2,asswave-0.04,asswave+0.04);
						Form9->Query7->SQL->Clear();
						Form9->Query7->SQL->Add(sqls);
						Form9->Query7->Open();
						Form9->Query7->First();
						float Ei=(Form9->Query7->FieldByName("Ei")->AsFloat)*1.23985e-4;


						float yyy=1.0;
                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
								{
								for (int k=0; k < Form10->Series1->Count(); k++)
										{
										if (wave < Form10->Series1->XValues->Value[k])
												{
												yyy=Form10->Series1->YValues->Value[k]+
												(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
												(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
												(wave-Form10->Series1->XValues->Value[k]);
												break;
												}
										}
								}
						else
								{
								yyy=1.0;
								}

						float delta=0.01;

						sprintf(sqls,"SELECT * FROM Stark where [Element] = '%s' and [Ion] = %i and ([Wavelength] between %f and %f )", ppp, 2,asswave-delta,asswave+delta);


						Form37->Query1->SQL->Clear();
						Form37->Query1->SQL->Add(sqls);
						Form37->Query1->Open();
						   Form37->Query1->First();


						float w5000=Form37->Query1->FieldByName("w-T5000")->AsFloat;
						float w10000=Form37->Query1->FieldByName("w-T10000")->AsFloat;


						float ws=w5000+(w10000-w5000)*(tem-5000.)/5000.;

						 float Dl=ws*2.*ne/1.e17*1.e-8;

						if (Dl==0) Dl=0.01*2.*ne/1.e17*1.e-8;

							   inte1/=yyy/Dl*1e30;
								float wcm=(asswave*1.e-8);
								ekk=1e17*pow(wcm,4)*f2*AnsiString(Form37->StringGrid2->Cells[3][jj]).ToDouble()*gk1*ak1*exp(-Ei/tem)/z2*(1.-exp(-(e1-Ei)/tem));
						   MySeries->AddXY(ekk,inte1);
							Form9->Query6->Next();
						  }
					  }

				 Form9->Query2->Next();
				   }

			   }
//---------------------------------------------------------------------------

void __fastcall TForm37::Button2Click(TObject *Sender)
{
void report (AnsiString nomereport, AnsiString nomefile, AnsiString nometempl);
double zZ(AnsiString spp,int ion,float ti);
Form9->SaveDialog1->Title="Save Report";
Form9->SaveDialog1->Filter="Report|*.REP";
Form9->SaveDialog1->FileName = "*.REP";
Form9->SaveDialog1->InitialDir="C:\\LIBS++\\Reports";
char stringa[80]="The file already exists. Overwrite?";
if (Form9->SaveDialog1->Execute())
	{
		if (FileExists(Form9->SaveDialog1->FileName))
		{
			if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
				mbCancel, 0) != IDYES)
				return;
		}

  FILE *out;

   out = fopen(AnsiString(Form9->SaveDialog1->FileName).c_str(), "w");
	for (int i=0; i < Form37->Chart1->SeriesCount(); i++)
  {
  float ppp=Form37->Chart1->Series[i]->Count();
   AnsiString snam=Form37->Chart1->Series[i]->Name;
  for (int j=0; j < ppp; j++)
  {
  float XX = Form37->Chart1->Series[i]->XValues->Value[j];
  float YY = Form37->Chart1->Series[i]->YValues->Value[j];
	 fprintf(out,"%s %1.2e %1.2e\n",snam,XX,YY);
   }
   }
					fclose(out);
		}

}
//---------------------------------------------------------------------------

